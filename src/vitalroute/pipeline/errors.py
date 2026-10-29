"""Structured pipeline failure evidence."""

class PipelineFailure(Exception):
    def __init__(self, stage, code, message, **evidence):
        super().__init__(message)
        self.stage, self.code, self.evidence = stage, code, evidence

    def document(self):
        return {"stage": self.stage, "code": self.code, "message": str(self), "evidence": self.evidence}
