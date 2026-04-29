from app.db.models import RuleModel

class DecisionEngine:
    def __init__(self):
        pass

    def evaluate_rules(self, ai_output: dict, db_session) -> tuple:
        rules = db_session.query(RuleModel).filter(RuleModel.is_active == True).all()
        
        triggered_rules = []
        final_decision = ai_output.get("decision")
        
        if ai_output.get("uncertainty") == True or ai_output.get("confidence", 1.0) < 0.6:
            final_decision = "manual_review"
            triggered_rules.append("system_uncertainty_threshold")
        
        for rule in rules:
            condition = rule.condition
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")
            
            if field in ai_output:
                actual_value = ai_output[field]
                match = False
                if operator == "<" and actual_value < value:
                    match = True
                elif operator == ">" and actual_value > value:
                    match = True
                elif operator == "==" and actual_value == value:
                    match = True
                
                if match:
                    triggered_rules.append(rule.name)
                    final_decision = rule.action
                    
        return final_decision, triggered_rules

decision_engine = DecisionEngine()
