const fs = require('fs');
const { chromium } = require('playwright');

const FRONTEND_URL = 'http://127.0.0.1:4174';
const BACKEND_URL = 'http://127.0.0.1:8001';
const SEED_PATH = 'D:\\workspace\\123\\ccc\\astrobiology\\backend\\tmp_smoke\\seed.json';

const seed = JSON.parse(fs.readFileSync(SEED_PATH, 'utf-8'));
const invalidPdf = {
  name: `targeted-invalid-${Date.now()}.pdf`,
  mimeType: 'application/pdf',
  buffer: Buffer.from('not a real pdf', 'utf-8'),
};

const result = {
  pdfDetail: {},
  meteoriteManagement: {},
  directProcessing: {},
  ragWorkspace: {},
  pageErrors: [],
  uncaughtConsoleErrors: [],
};

function normalizeText(text) {
  return (text || '').replace(/\s+/g, ' ').trim();
}

function isReadable(text) {
  return !!text && !/\[object Object\]|Traceback|<html|<!doctype|undefined|null/i.test(text);
}

async function collectMessages(page) {
  const selectors = [
    '.el-message .el-message__content',
    '.notification-message',
    '.notification-title',
    '.error-notification .notification-message',
    '.message-wrapper.ai .message-text',
  ];
  const values = [];
  for (const selector of selectors) {
    const locator = page.locator(selector);
    const count = await locator.count();
    for (let i = 0; i < Math.min(count, 6); i += 1) {
      const item = locator.nth(i);
      if (await item.isVisible().catch(() => false)) {
        const text = normalizeText(await item.innerText().catch(() => ''));
        if (text) values.push(text);
      }
    }
  }
  return [...new Set(values)];
}

async function waitForMessage(page, matcher = null, timeout = 12000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    const messages = await collectMessages(page);
    const match = matcher
      ? messages.find((item) => matcher.test(item))
      : messages.find(Boolean);
    if (match) return match;
    await page.waitForTimeout(250);
  }
  return '';
}

async function clickPrimaryDialogButton(page) {
  const dialog = page.locator('.el-message-box');
  if (await dialog.isVisible().catch(() => false)) {
    await dialog.locator('.el-button--primary').click();
    return true;
  }
  return false;
}

async function waitForReady(url, marker, timeout = 120000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    try {
      const res = await fetch(url);
      const text = await res.text();
      if (res.ok && text.includes(marker)) return true;
    } catch (error) {
      // ignore during boot
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function loginAdmin(page) {
  await page.goto(`${FRONTEND_URL}/admin`, { waitUntil: 'networkidle' });
  await page.locator('input').nth(0).fill(seed.admin.username);
  await page.locator('input[type="password"]').fill(seed.admin.password);
  await page.getByRole('button').filter({ hasText: /登录|Login/ }).click();
  await page.waitForFunction(() => {
    return window.localStorage.getItem('token') && window.localStorage.getItem('admin_logged_in') === 'true';
  }, { timeout: 30000 });
  await page.waitForTimeout(1000);
}

async function testPdfDetail(page) {
  const documentId = seed.documents.single_success.id;
  const seenResponses = [];

  const handler = async (response) => {
    const url = response.url();
    if (
      url.includes('/api/pdf/documents/chunks/') ||
      url.includes(`/api/pdf/documents/${documentId}/`) ||
      /\/api\/pdf\/documents\/(NaN|\d+)\/$/.test(url)
    ) {
      seenResponses.push({ url, status: response.status() });
    }
  };

  page.on('response', handler);
  await page.goto(`${FRONTEND_URL}/pdf-detail/${documentId}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  const title = normalizeText(await page.locator('h1').first().innerText().catch(() => ''));
  const detailRequest = seenResponses.find((item) => item.url.includes(`/api/pdf/documents/${documentId}/`));
  const chunkRequest = seenResponses.find((item) => item.url.includes('/api/pdf/documents/chunks/'));
  const badIdRequest = seenResponses.find((item) => /\/api\/pdf\/documents\/(NaN|\d+)\/$/.test(item.url));

  result.pdfDetail.directRoute = {
    passed: Boolean(title) && detailRequest?.status === 200 && chunkRequest?.status === 200 && !badIdRequest,
    title,
    detailRequest,
    chunkRequest,
    badIdRequest: badIdRequest || null,
  };

  seenResponses.length = 0;
  await page.goto(`${FRONTEND_URL}/index.html`, { waitUntil: 'networkidle' });
  await page.evaluate((id) => {
    window.history.pushState({}, '', `/admin/pdf-detail/${id}`);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }, documentId);
  await page.waitForTimeout(1500);
  const legacyTitle = normalizeText(await page.locator('h1').first().innerText().catch(() => ''));
  const legacyDetailRequest = seenResponses.find((item) => item.url.includes(`/api/pdf/documents/${documentId}/`));
  const legacyBadIdRequest = seenResponses.find((item) => /\/api\/pdf\/documents\/(NaN|\d+)\/$/.test(item.url));

  result.pdfDetail.legacyRoute = {
    passed: Boolean(legacyTitle) && legacyDetailRequest?.status === 200 && !legacyBadIdRequest,
    title: legacyTitle,
    detailRequest: legacyDetailRequest || null,
    badIdRequest: legacyBadIdRequest || null,
  };

  page.off('response', handler);
}

async function testMeteoriteManagement(page) {
  await page.goto(`${FRONTEND_URL}/admin/meteorite-management`, { waitUntil: 'networkidle' });
  const uniqueName = `Smoke Targeted ${Date.now()}`;
  await page.locator('.toolbar .btn.btn-primary').click();
  const modal = page.locator('.modal-content').last();
  const inputs = modal.locator('input');
  await inputs.nth(0).fill(uniqueName);
  await inputs.nth(1).fill('Chondrite');
  await inputs.nth(2).fill('Targeted Lab');
  await inputs.nth(3).fill('Mars');
  await modal.locator('textarea').nth(0).fill('glycine, alanine');
  await modal.locator('textarea').nth(1).fill('clean bench');
  await inputs.nth(4).fill('0.91');
  await inputs.nth(5).fill('targeted-smoke');
  await modal.locator('textarea').nth(2).fill('targeted reference');
  await page.getByRole('button', { name: /保存|Save/ }).click();

  const saveMessage = await waitForMessage(page, /成功|保存/);
  const searchInput = page.locator('.search-box input');
  await searchInput.waitFor({ timeout: 10000 });
  const searchValue = await searchInput.inputValue();
  const row = page.locator('tr', { hasText: uniqueName }).first();
  await row.waitFor({ timeout: 15000 });

  result.meteoriteManagement.saveChain = {
    passed: isReadable(saveMessage) && searchValue === uniqueName && await row.isVisible(),
    message: saveMessage,
    searchValue,
  };

  const statusButtons = page.locator('.status-quick-actions button');
  result.meteoriteManagement.statusSwitch = {
    passed: false,
    reason: (await statusButtons.count()) > 0 ? '控件存在但本轮未切换' : '当前页面未渲染状态切换控件',
  };

  await row.locator('.btn-delete').click();
  await clickPrimaryDialogButton(page);
  const deleteMessage = await waitForMessage(page, /删除/);
  await page.waitForTimeout(1000);
  result.meteoriteManagement.deleteChain = {
    passed: isReadable(deleteMessage),
    message: deleteMessage,
    rowStillVisible: await row.isVisible().catch(() => false),
  };
}

async function testDirectProcessing(page) {
  await page.goto(`${FRONTEND_URL}/admin/direct-processing`, { waitUntil: 'networkidle' });
  const input = page.locator('.direct-processing-container input[type="file"]');

  await input.setInputFiles(seed.files.upload_valid);
  await page.getByRole('button', { name: /开始上传|Start Upload/ }).click();
  const successMessage = await waitForMessage(page, /成功|处理/);
  const historyRow = page.locator('.el-table__body-wrapper tbody tr').first();
  await historyRow.waitFor({ timeout: 120000 });

  result.directProcessing.uploadSuccess = {
    passed: isReadable(successMessage),
    message: successMessage,
  };

  await historyRow.getByRole('button', { name: /查看|View/ }).click();
  const viewMessage = await waitForMessage(page, /查看|结果|成功/);
  result.directProcessing.viewResult = {
    passed: isReadable(viewMessage) || (await page.locator('.result-item').count()) > 0,
    message: viewMessage || '结果区域已显示',
  };

  await historyRow.getByRole('button', { name: /删除|Delete/ }).click();
  await clickPrimaryDialogButton(page);
  const deleteMessage = await waitForMessage(page, /删除/);
  result.directProcessing.deleteHistory = {
    passed: isReadable(deleteMessage),
    message: deleteMessage,
  };

  await input.setInputFiles(invalidPdf);
  await page.getByRole('button', { name: /开始上传|Start Upload/ }).click();
  const failureMessage = await waitForMessage(page, /失败|无效|PDF/);
  result.directProcessing.uploadFailure = {
    passed: isReadable(failureMessage),
    message: failureMessage,
  };
}

async function testWorkspaceQa(page) {
  await page.goto(`${FRONTEND_URL}/workspace?tab=qa`, { waitUntil: 'networkidle' });
  const qaTab = page.locator('.workspace-tabs .tab-button', { hasText: /AI Q&A/ }).first();
  await qaTab.waitFor({ timeout: 20000 });
  await qaTab.click();
  await page.locator('textarea').fill('Summarize the key topic of this astrobiology system in one paragraph.');
  await page.locator('.send-btn').click();
  await page.waitForFunction(() => {
    const items = document.querySelectorAll('.message-wrapper.ai .message-text');
    return items.length > 0 && items[items.length - 1].textContent.trim().length > 0;
  }, { timeout: 120000 });
  const aiMessages = page.locator('.message-wrapper.ai .message-text');
  const successMessage = normalizeText(await aiMessages.last().innerText());
  result.ragWorkspace.success = {
    passed: Boolean(successMessage),
    message: successMessage.slice(0, 200),
  };

  const failureRoute = '**/api/pdf/unified/question/';
  await page.route(failureRoute, async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify({ success: false, message: '问答失败（定点冒烟）' }),
    });
  });
  await page.locator('textarea').fill('Trigger QA failure');
  await page.locator('.send-btn').click();
  await page.waitForFunction(() => {
    const items = document.querySelectorAll('.message-wrapper.ai .message-text');
    return items.length > 0 && /失败/.test(items[items.length - 1].textContent);
  }, { timeout: 20000 });
  const failureMessage = normalizeText(await aiMessages.last().innerText());
  await page.unroute(failureRoute);

  result.ragWorkspace.failure = {
    passed: /失败/.test(failureMessage) && isReadable(failureMessage),
    message: failureMessage,
  };
}

async function main() {
  await waitForReady(`${FRONTEND_URL}/index.html`, '<!DOCTYPE html>');
  await waitForReady(`${BACKEND_URL}/api/pdf/health/`, 'success');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);

  page.on('pageerror', (error) => {
    result.pageErrors.push(normalizeText(error.message || String(error)));
  });
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = normalizeText(msg.text());
      if (/Unhandled|uncaught/i.test(text)) {
        result.uncaughtConsoleErrors.push(text);
      }
    }
  });

  try {
    await loginAdmin(page);
    await testPdfDetail(page);
    await testMeteoriteManagement(page);
    await testDirectProcessing(page);
    await testWorkspaceQa(page);
  } finally {
    await browser.close();
  }

  console.log(JSON.stringify(result, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
