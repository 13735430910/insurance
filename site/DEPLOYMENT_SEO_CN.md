# SeguroTools 上线与 SEO 配置清单

## 推荐托管方式

长期维护建议使用 Cloudflare Pages 的 GitHub 同步，而不是只做本地 direct upload。

原因：

- 每次更新知识库、文章或计算器后，只要 push 到 GitHub，Cloudflare 自动重新构建。
- `functions/` 目录里的邮件 API 会随站点一起部署，不需要单独维护 Worker。
- 构建配置、环境变量、Secrets 和自定义域名都能在 Cloudflare Pages 项目里集中管理。

当前仓库：

```text
13735430910/insurance
```

Cloudflare Pages 项目建议：

```text
Project name: segurotools
Production branch: master
Project root: site
Build command: python3 build.py
Build output directory: dist
Functions directory: functions
Custom domain: segurotools.com
```

## Cloudflare 后台操作

1. 进入 Cloudflare Dashboard > Workers & Pages > Create application > Pages。
2. 选择 Connect to Git，授权 GitHub，并选择 `13735430910/insurance`。
3. 按上面的项目配置填写构建参数。
4. 在 Settings > Environment variables 添加生产环境变量：

```text
OWNER_EMAIL=segruotools@gmail.com
FORWARD_EMAIL=segruotools@gmail.com
FROM_EMAIL=reports@segurotools.com
INBOUND_FROM_EMAIL=forwarder@segurotools.com
INBOUND_DOMAIN=segurotools.com
```

5. 添加生产环境 Secrets：

```text
RESEND_API_KEY=...
RESEND_WEBHOOK_SECRET=...
```

6. 首次部署成功后，在 Pages 项目 > Custom domains 添加：

```text
segurotools.com
```

如果使用 CLI/API 自动部署，Cloudflare API token 至少需要 Pages 项目读写权限。当前 `.env` 中的 token 能识别账号，但访问 Pages API 返回认证错误，需要在 Cloudflare 后台重新创建或调整 token 权限。

## Resend 邮件配置

出站邮件：

- 验证 `segurotools.com` 发送域名。
- 确认 `reports@segurotools.com` 和 `forwarder@segurotools.com` 可以作为发件地址。

入站转发：

1. 在 Resend Receiving 中启用 `segurotools.com`。
2. 确认 MX 记录由 Resend 接管。
3. 在 Resend Webhooks 添加：

```text
Endpoint: https://segurotools.com/api/inbound-email
Event: email.received
```

4. 把 webhook secret 填入 Cloudflare Pages secret：

```text
RESEND_WEBHOOK_SECRET=...
```

当前 Worker 会校验 Resend/Svix 签名，只转发发给 `@segurotools.com` 的邮件，并统一转发到 `segruotools@gmail.com`。

## Google Search Console 配置

1. 打开 Google Search Console，添加 Domain property：

```text
segurotools.com
```

2. Google 会给一个 DNS TXT 记录。到 Cloudflare DNS 中添加该 TXT 记录，等待验证通过。
3. 验证后进入 Sitemaps，提交：

```text
https://segurotools.com/sitemap.xml
```

4. 用 URL Inspection 检查并请求索引这些首批页面：

```text
https://segurotools.com/en/
https://segurotools.com/es/
https://segurotools.com/en/calculators/
https://segurotools.com/es/calculadoras/
https://segurotools.com/en/contact/
https://segurotools.com/es/contact/
```

5. 上线后 2-4 周，在 Performance 中导出查询词，优先补强有展示但点击率低的页面标题、摘要和内链。

## SEO 优化方向

当前站点已经生成：

- `sitemap.xml`
- `robots.txt`
- canonical URL
- 英语/西语 `hreflang`
- 文章、分类、知识库、计算器之间的内链
- Contact、Privacy、Disclaimer、Terms、Author 页面

后续重点：

- 避开巨头词，优先做长尾问题，例如自雇 ACA、移民家庭医保、rideshare/delivery 车险责任缺口、租客洪水缺口、final expense 预算、pet insurance break-even。
- 每篇 YMYL 保险内容保留官方来源路径，优先 NAIC、CMS、Medicare、Healthcare.gov、FEMA、FTC、IRS、SBA、州 DOI。
- 建州级页面时只写有官方来源支持的规则、费率背景和生效日期，不泛化到全国。
- 西语页面不要机械翻译英文页，要保留美国保险常用英文术语和西语解释，例如 deductible/deducible、premium/prima、claim/reclamacion。
- AdSense 申请前人工复审 About、Contact、Privacy、Disclaimer、Terms、Author 页面，以及所有高风险保险建议表述。
- 后续可增加 FAQ 结构化数据，但页面上必须真实展示相同问答内容。

## 上线后检查

```text
https://segurotools.com/robots.txt
https://segurotools.com/sitemap.xml
https://segurotools.com/en/contact/
https://segurotools.com/api/send-report
https://segurotools.com/api/inbound-email
```

`/api/send-report` 和 `/api/inbound-email` 的 GET 请求不需要返回正常页面；重点是 POST 请求在 Cloudflare Pages Functions 中可用。
