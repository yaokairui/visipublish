"""ApiChannel：官方开放平台 API 渠道骨架（尚未实现）。

设计说明（未来接入真实平台时的路线）：
- 拼多多：open.pinduoduo.com，`pdd.goods.add` 直接发布或建草稿；需企业实名 + 按量预充值，是门槛最低的官方 API 渠道。
- 1688：open.1688.com，`alibaba.product.add` 发布；需企业实名 + 应用审核，高级接口购买资源包。
- 抖店：op.jinritemai.com，`/product/add` 发布、`/product/setOnSale` 上架、`/product/setOffline` 下架；需企业/个体户 + 软著审核。
- 淘宝/京东：企业资质 + 应用审核 + 店铺 OAuth 授权（部分接口要求部署聚石塔），个人号基本拿不到发布权限。

接入步骤（骨架就绪后）：
1. 在 __init__ 中读取平台 app_key / app_secret / access_token（环境变量或登录态文件，勿硬编码）。
2. 实现 check_ready：校验凭证是否存在且未过期（必要时调 token 刷新）。
3. 实现 publish：把通用 listing payload 映射为平台字段（类目树 / 必填属性 / 图片尺寸差异在此收敛），
   携带 idempotency_key 做幂等（如 sku 前缀 + 业务键）。
4. 实现 publish_off：调用平台下架接口，按商品 ID 操作。
5. 在 registry.py 注册该渠道，CHANNEL=xxx 即可切换，无需改 app.py。
"""
from src.channels.base import BaseChannel, ChannelResult


class ApiChannel(BaseChannel):
    """官方开放平台 API 渠道骨架：契约已定义，实现待接入。"""

    name = "api"

    @classmethod
    def create(cls) -> "ApiChannel":
        return cls()

    def check_ready(self) -> tuple[bool, str]:
        return False, "ApiChannel 尚未实现：需先接入拼多多 / 1688 等开放平台的凭证与应用审核"

    def publish(self, item: dict) -> ChannelResult:
        raise NotImplementedError("ApiChannel.publish 未实现：请先接入官方开放平台")

    def publish_off(self, item: dict) -> ChannelResult:
        raise NotImplementedError("ApiChannel.publish_off 未实现：请先接入官方开放平台")