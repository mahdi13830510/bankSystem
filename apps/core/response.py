from rest_framework.response import Response


class APIResponse:

    @staticmethod
    def success(data=None, message="success"):
        return Response({
            "status": "success",
            "message": message,
            "data": data
        })

    @staticmethod
    def error(message="error", status_code=400):
        return Response({
            "status": "error",
            "message": message
        }, status=status_code)