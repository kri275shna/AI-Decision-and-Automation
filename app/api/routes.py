from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
import uuid

from app.db.database import get_db
from app.db.models import RequestModel, WorkflowModel, AIOutputModel, IdempotencyKeyModel, RuleModel
from app.schemas.schemas import TicketInput, TicketResponse, RuleCreate, RuleResponse, ExplainResponse
from app.queue.in_memory_queue import task_queue

router = APIRouter()

@router.post("/requests", response_model=TicketResponse, status_code=202)
def create_request(
    ticket: TicketInput, 
    idempotency_key: str = Header(None), 
    db: Session = Depends(get_db)
):
    if idempotency_key:
        existing_key = db.query(IdempotencyKeyModel).filter(IdempotencyKeyModel.idempotency_key == idempotency_key).first()
        if existing_key:
            return existing_key.response_body

    request_id = f"req_{uuid.uuid4().hex[:12]}"
    
    req_model = RequestModel(
        id=request_id,
        input_text=f"{ticket.subject} {ticket.description}",
        input_metadata=ticket.model_dump(),
        status="INIT"
    )
    db.add(req_model)
    
    wf_model = WorkflowModel(request_id=request_id, state="INIT")
    db.add(wf_model)
    db.commit()

    response_data = {"request_id": request_id, "status": "INIT", "message": "Request accepted"}
    
    if idempotency_key:
        idem_model = IdempotencyKeyModel(
            idempotency_key=idempotency_key,
            request_id=request_id,
            response_body=response_data
        )
        db.add(idem_model)
        db.commit()

    task_queue.enqueue({"request_id": request_id})

    return response_data

@router.get("/requests/{request_id}")
def get_request(request_id: str, db: Session = Depends(get_db)):
    req = db.query(RequestModel).filter(RequestModel.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    return {
        "request_id": req.id,
        "status": req.status,
        "input": req.input_metadata
    }

@router.get("/requests/{request_id}/explain", response_model=ExplainResponse)
def explain_request(request_id: str, db: Session = Depends(get_db)):
    req = db.query(RequestModel).filter(RequestModel.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    wf = db.query(WorkflowModel).filter(WorkflowModel.request_id == request_id).first()
    ai_out = db.query(AIOutputModel).filter(AIOutputModel.request_id == request_id).first()
    audits = req.audit_logs
    
    rules_triggered = []
    failure_reasons = []
    for audit in audits:
        if audit.new_state == "FAILED":
            failure_reasons.append(audit.reason)
        if audit.new_state in ["SUCCESS", "MANUAL_REVIEW"] and "Rules triggered:" in audit.reason:
            parts = audit.reason.split("Rules triggered: ")
            if len(parts) > 1:
                rules_part = parts[1].split(".")[0]
                if rules_part != "[]":
                    rules_triggered.append(rules_part)

    return {
        "request_id": req.id,
        "input_data": req.input_metadata,
        "retrieved_context": ai_out.retrieved_context if ai_out else [],
        "ai_output": ai_out.raw_output if ai_out else None,
        "rules_triggered": rules_triggered,
        "final_decision": ai_out.decision if ai_out else None,
        "confidence_score": ai_out.confidence if ai_out else None,
        "failure_reasons": "; ".join(failure_reasons) if failure_reasons else None,
        "current_state": wf.state if wf else "UNKNOWN"
    }

@router.post("/rules", response_model=RuleResponse)
def create_rule(rule: RuleCreate, db: Session = Depends(get_db)):
    db_rule = RuleModel(**rule.model_dump())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.put("/rules/{rule_id}", response_model=RuleResponse)
def update_rule(rule_id: int, rule_update: RuleCreate, db: Session = Depends(get_db)):
    db_rule = db.query(RuleModel).filter(RuleModel.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
        
    for k, v in rule_update.model_dump().items():
        setattr(db_rule, k, v)
        
    db.commit()
    db.refresh(db_rule)
    return db_rule
