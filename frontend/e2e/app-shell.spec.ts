import { expect, test } from "@playwright/test";

test("login screen is available through the overview deep link", async ({ page }) => {
  await page.goto("/overview");
  await expect(page.locator("h1")).toContainText("把供应链的");
  await expect(page.locator("h1")).toContainText("下一步");
  await expect(page.getByLabel("组织标识")).toBeVisible();
  await expect(page.getByRole("button", { name: "登录工作区" })).toBeEnabled();
  await page.screenshot({ path: "../output/playwright/login-desktop.png", fullPage: true });
});

test("login controls preserve accessible labels", async ({ page }) => {
  await page.goto("/analysis");
  await page.getByLabel("登录邮箱").fill("admin@demo.local");
  await expect(page.getByLabel("登录邮箱")).toHaveValue("admin@demo.local");
  await page.getByLabel("显示密码").click();
  await expect(page.getByLabel("隐藏密码")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "../output/playwright/login-mobile.png", fullPage: true });
});

test("administrator can enter the operations overview", async ({ page }) => {
  await page.goto("/overview");
  await page.getByLabel("登录邮箱").fill("admin@demo.local");
  await page.getByLabel("登录密码").fill("ChangeMe123!");
  await page.getByLabel("组织标识").fill("demo-factory");
  await page.getByRole("button", { name: "登录工作区" }).click();
  await expect(page.getByRole("heading", { name: "运营总览" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("navigation", { name: "主导航" })).toBeVisible();
  await page.screenshot({ path: "../output/playwright/overview-desktop.png", fullPage: true });
});

test("administrator navigation keeps domain URLs in sync", async ({ page }) => {
  await page.goto("/overview");
  await page.getByLabel("登录邮箱").fill("admin@demo.local");
  await page.getByLabel("登录密码").fill("ChangeMe123!");
  await page.getByLabel("组织标识").fill("demo-factory");
  await page.getByRole("button", { name: "登录工作区" }).click();
  await expect(page.getByRole("heading", { name: "运营总览" })).toBeVisible({ timeout: 15_000 });
  const navigation = page.getByRole("navigation", { name: "主导航" });
  await navigation.getByRole("button", { name: /数据源/ }).click();
  await expect(page).toHaveURL(/\/data-sources$/);
  await expect(page.locator("h1", { hasText: "数据源" })).toBeVisible();
  await navigation.getByRole("button", { name: /知识库/ }).click();
  await expect(page).toHaveURL(/\/knowledge$/);
  await expect(page.locator("h1", { hasText: "知识库" })).toBeVisible();
  await navigation.getByRole("button", { name: /报告中心/ }).click();
  await expect(page).toHaveURL(/\/reports$/);
  await expect(page.locator("h1", { hasText: "报告中心" })).toBeVisible();
});

test("mobile navigation prioritizes daily work and exposes enterprise pages through more", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/overview");
  await page.getByLabel("登录邮箱").fill("admin@demo.local");
  await page.getByLabel("登录密码").fill("ChangeMe123!");
  await page.getByLabel("组织标识").fill("demo-factory");
  await page.getByRole("button", { name: "登录工作区" }).click();
  const navigation = page.getByRole("navigation", { name: "移动主导航" });
  await expect(navigation.getByRole("button", { name: "分析会话" })).toBeVisible({ timeout: 15_000 });
  await navigation.getByRole("button", { name: "更多" }).click();
  await page.getByRole("region", { name: "更多工作区功能" }).getByRole("button", { name: "报告中心" }).click();
  await expect(page).toHaveURL(/\/reports$/);
  await expect(page.locator("h1", { hasText: "报告中心" })).toBeVisible();
  await page.screenshot({ path: "../output/playwright/mobile-more-navigation.png", fullPage: true });
});

test("viewer is redirected away from a restricted deep link", async ({ page }) => {
  await page.goto("/audit");
  await page.getByLabel("登录邮箱").fill("viewer@demo.local");
  await page.getByLabel("登录密码").fill("ChangeMe123!");
  await page.getByLabel("组织标识").fill("demo-factory");
  await page.getByRole("button", { name: "登录工作区" }).click();
  await expect(page).toHaveURL(/\/overview$/, { timeout: 15_000 });
  await expect(page.getByRole("navigation", { name: "主导航" }).getByRole("button", { name: "组织与审计" })).toHaveCount(0);
});

test("administrator can inspect the real operational resource paths", async ({ page }) => {
  await page.goto("/overview");
  await page.getByLabel("登录邮箱").fill("admin@demo.local");
  await page.getByLabel("登录密码").fill("ChangeMe123!");
  await page.getByLabel("组织标识").fill("demo-factory");
  await page.getByRole("button", { name: "登录工作区" }).click();
  await expect(page.getByRole("heading", { name: "运营总览" })).toBeVisible({ timeout: 15_000 });
  await page.getByLabel("时间范围").selectOption("7d");
  await expect(page.getByLabel("时间范围")).toHaveValue("7d");
  const navigation = page.getByRole("navigation", { name: "主导航" });
  await navigation.getByRole("button", { name: /数据源/ }).click();
  await page.locator(".datasource-row .row-main-button").first().click();
  await expect(page.locator(".detail-panel h3")).toBeVisible();
  await navigation.getByRole("button", { name: /知识库/ }).click();
  await page.getByRole("button", { name: /管理详情/ }).first().click();
  await expect(page.getByPlaceholder("预览检索，例如：生产达成率口径")).toBeVisible();
  await navigation.getByRole("button", { name: /报告中心/ }).click();
  await page.locator(".list-row .row-main-button").first().click();
  await expect(page.locator(".report-detail")).toBeVisible();
});

test("analysis history opens inside a contained session window", async ({ page }) => {
  await page.goto("/analysis");
  await page.getByLabel("登录邮箱").fill("admin@demo.local");
  await page.getByLabel("登录密码").fill("ChangeMe123!");
  await page.getByLabel("组织标识").fill("demo-factory");
  await page.getByRole("button", { name: "登录工作区" }).click();
  await page.getByRole("navigation", { name: "主导航" }).getByRole("button", { name: /分析会话/ }).click();
  const history = page.locator(".analysis-history-row").first();
  await expect(history).toBeVisible({ timeout: 15_000 });
  await history.click();
  const sessionWindow = page.locator(".analysis-session-window");
  await expect(sessionWindow).toBeVisible();
  await expect(sessionWindow.getByText("运行 ID：")).toBeVisible();
  await expect(sessionWindow.locator(".step-timeline")).toBeVisible();
  await sessionWindow.getByRole("button", { name: "关闭" }).click();
  await expect(sessionWindow).toBeHidden();
});

test("administrator receives a streamed analysis conclusion from active resources", async ({ page }) => {
  await page.goto("/analysis");
  await page.getByLabel("登录邮箱").fill("admin@demo.local");
  await page.getByLabel("登录密码").fill("ChangeMe123!");
  await page.getByLabel("组织标识").fill("demo-factory");
  await page.getByRole("button", { name: "登录工作区" }).click();
  await expect(page.getByRole("heading", { name: "运营总览" })).toBeVisible({ timeout: 15_000 });
  await page.getByRole("navigation", { name: "主导航" }).getByRole("button", { name: /分析会话/ }).click();
  await expect(page.locator("h2", { hasText: "分析会话" })).toBeVisible({ timeout: 15_000 });
  await page.getByLabel("数据源").selectOption({ index: 1 });
  await page.getByLabel("知识库").selectOption({ index: 1 });
  await page.getByLabel("分析问题").fill("近30天各工厂生产达成率与缺料风险");
  await page.getByRole("button", { name: "开始分析" }).click();
  await expect(page.getByText("实时运行状态")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("任务已创建")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("结论已生成")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("分析完成")).toBeVisible();
  await expect(page.getByText(/已验证 \d+ 条结果/)).toBeVisible();
});
