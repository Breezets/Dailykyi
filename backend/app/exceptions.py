"""应用自定义异常与统一处理器：所有错误以 { code, message, detail } 返回。"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger


def _error(code: int, message: str, detail: object = None) -> JSONResponse:
    return JSONResponse(
        status_code=code if 100 <= code < 600 else 500,
        content={"code": code, "message": message, "detail": detail},
    )


class DailykyiError(Exception):
    """自定义业务异常基类。"""

    def __init__(self, message: str = "服务异常", code: int = 500, detail: object = None):
        self.message = message
        self.code = code
        self.detail = detail
        super().__init__(message)


class AccountNotFound(DailykyiError):
    def __init__(self, message: str = "账号不存在"):
        super().__init__(message, code=404)


class TaskConfigError(DailykyiError):
    def __init__(self, message: str = "任务配置错误"):
        super().__init__(message, code=400)


class BiliAPIError(DailykyiError):
    def __init__(self, message: str = "B 站 API 调用失败", detail: object = None):
        super().__init__(message, code=502, detail=detail)


class BiliAPIException(BiliAPIError):
    """B 站 API 异常：带 message 和 code 字段。"""

    def __init__(self, message: str = "B 站 API 调用失败", code: int = 502) -> None:
        super().__init__(message, detail=None)
        self.code = code


class TaskExecuteException(DailykyiError):
    """任务执行异常：带 message 和 code 字段。"""

    def __init__(self, message: str = "任务执行失败", code: int = 500) -> None:
        super().__init__(message, code=code)


def register_exception_handlers(app: FastAPI) -> None:
    """注册统一异常处理器。"""

    @app.exception_handler(DailykyiError)
    async def _dailykyi_handler(_: Request, exc: DailykyiError) -> JSONResponse:
        logger.warning(f"业务异常: {exc.message}")
        return _error(exc.code, exc.message, exc.detail)

    @app.exception_handler(BiliAPIException)
    async def _bili_api_handler(_: Request, exc: BiliAPIException) -> JSONResponse:
        logger.warning(f"B 站 API 异常: {exc.message}")
        return _error(exc.code, exc.message)

    @app.exception_handler(TaskExecuteException)
    async def _task_exec_handler(_: Request, exc: TaskExecuteException) -> JSONResponse:
        logger.warning(f"任务执行异常: {exc.message}")
        return _error(exc.code, exc.message)

    @app.exception_handler(HTTPException)
    async def _http_handler(_: Request, exc: HTTPException) -> JSONResponse:
        logger.warning(f"HTTP 异常: {exc.status_code} {exc.detail}")
        return _error(exc.status_code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning(f"参数校验失败: {exc.errors()}")
        return _error(422, "请求参数校验失败", exc.errors())

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"未捕获异常: {exc}")
        return _error(500, "服务器内部错误")
