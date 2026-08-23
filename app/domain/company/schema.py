from pydantic import BaseModel


class KisStockInfoOutput(BaseModel):
    std_idst_clsf_cd_name: str | None = None
    std_idst_clsf_cd: str | None = None


class KisStockInfoResponse(BaseModel):
    rt_cd: str
    msg_cd: str | None = None
    msg1: str | None = None
    output: KisStockInfoOutput | None = None
