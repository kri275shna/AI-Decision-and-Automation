import time
from app.db.database import SessionLocal
from app.db.models import RequestModel, AIOutputModel, WorkflowModel, AuditLogModel
from app.engine.ai_engine import ai_engine
from app.engine.rag_engine import rag_engine
from app.engine.decision_engine import decision_engine
from app.utils.logger import logger

class WorkflowEngine:
    def process_task(self, task_data: dict):
        request_id = task_data.get("request_id")
        is_dead_letter = task_data.get("_dead_letter", False)
        error_msg = task_data.get("_error", "")
        
        db = SessionLocal()
        try:
            req = db.query(RequestModel).filter(RequestModel.id == request_id).first()
            wf = db.query(WorkflowModel).filter(WorkflowModel.request_id == request_id).first()
            
            if not req or not wf:
                logger.error(f"Request {request_id} not found in DB")
                return

            if is_dead_letter:
                self._transition_state(db, req, wf, "FAILED", f"Max retries reached. Last error: {error_msg}")
                return

            if wf.state in ["SUCCESS", "FAILED", "MANUAL_REVIEW"]:
                logger.info(f"Request {request_id} already in terminal state {wf.state}")
                return

            self._transition_state(db, req, wf, "PROCESSING", "Started processing")

            start_time = time.time()
            input_text = f"{req.input_metadata.get('subject', '')} {req.input_metadata.get('description', '')}"
            context = rag_engine.retrieve(input_text)
            
            self._transition_state(db, req, wf, "AI_EVALUATION", "Calling AI Engine")
            ai_output_data = ai_engine.evaluate_ticket(req.input_metadata, context)
            
            final_decision, triggered_rules = decision_engine.evaluate_rules(ai_output_data, db)
            
            ai_model = AIOutputModel(
                request_id=request_id,
                retrieved_context=context,
                raw_output=ai_output_data,
                decision=final_decision,
                confidence=ai_output_data.get("confidence"),
                uncertainty=ai_output_data.get("uncertainty")
            )
            db.add(ai_model)
            
            reason = f"AI decision: {ai_output_data.get('decision')}. Rules triggered: {triggered_rules}. Final: {final_decision}"
            
            if final_decision == "manual_review":
                next_state = "MANUAL_REVIEW"
            else:
                next_state = "SUCCESS"
                
            self._transition_state(db, req, wf, next_state, reason)
            
            latency = time.time() - start_time
            logger.info("Processing completed", extra={"request_id": request_id, "state": next_state, "latency": latency})

        except Exception as e:
            logger.error(f"Workflow error: {str(e)}", extra={"request_id": request_id}, exc_info=True)
            db.rollback()
            if req and wf:
                wf.error_message = str(e)
                self._transition_state(db, req, wf, "RETRY", f"Error: {str(e)}")
            raise e
        finally:
            db.close()

    def _transition_state(self, db, req, wf, new_state, reason):
        old_state = wf.state
        if old_state != new_state:
            wf.state = new_state
            req.status = new_state
            
            audit = AuditLogModel(
                request_id=req.id,
                old_state=old_state,
                new_state=new_state,
                reason=reason
            )
            db.add(audit)
            db.commit()
            logger.info(f"State transition: {old_state} -> {new_state}", extra={"request_id": req.id, "state": new_state})

workflow_engine = WorkflowEngine()
