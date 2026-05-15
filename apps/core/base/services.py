class BaseService:

    @staticmethod
    def success(data=None):
        return {"status": "success", "data": data}

    @staticmethod
    def fail(message):

        return {"status": "error", "message": message}

