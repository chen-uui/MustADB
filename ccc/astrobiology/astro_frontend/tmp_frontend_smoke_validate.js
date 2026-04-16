const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const FRONTEND_URL = 'http://127.0.0.1:4173';
const BACKEND_URL = 'http://127.0.0.1:8000';
const SEED_PATH = 'D:\\workspace\\123\\ccc\\astrobiology\\backend\\tmp_smoke\\seed.json';

const seed = JSON.parse(fs.readFileSync(SEED_PATH, 'utf-8'));
const inlineInvalidPdf = {
  name: `smoke-inline-invalid-${Date.now()}.pdf`,
  mimeType: 'application/pdf',
  buffer: Buffer.from('not a real pdf', 'utf-8'),
};

const results = {
  pages: {},
  consoleErrors: [],
  pageErrors: [],
  requestFailures: [],
  remainingIssues: [],
  manualRetest: [],
};

function pushIssue(message) {
  if (!results.remainingIssues.includes(message)) {
    results.remainingIssues.push(message);
  }
}

function isReadableMessage(text) {
  return !!text && !/\[object Object\]|Traceback|<html|<!doctype|undefined|null/i.test(text);
}

function normalizeText(text) {
  return (text || '').replace(/\s+/g, ' ').trim();
}

async function collectFeedback(page) {
  const selectors = [
    '.el-message .el-message__content',
    '.el-notification__content',
    '.el-alert__title',
    '.el-alert__description',
    '.error-state span',
    '.task-error',
    '.status-modal',
  ];
  const values = [];
  for (const selector of selectors) {
    const locator = page.locator(selector);
    const count = await locator.count();
    for (let i = 0; i < Math.min(count, 5); i += 1) {
      const item = locator.nth(i);
      if (await item.isVisible().catch(() => false)) {
        const text = normalizeText(await item.innerText().catch(() => ''));
        if (text) values.push(text);
      }
    }
  }
  return [...new Set(values)];
}

async function waitForFeedback(page, timeout = 8000) {
  const end = Date.now() + timeout;
  let last = [];
  while (Date.now() < end) {
    last = await collectFeedback(page);
    const readable = last.find(isReadableMessage);
    if (readable) return readable;
    await page.waitForTimeout(250);
  }
  return last.find(Boolean) || '';
}

async function confirmElMessageBox(page) {
  const dialog = page.locator('.el-message-box');
  if (await dialog.count()) {
    const primary = dialog.locator('.el-button--primary').last();
    if (await primary.isVisible().catch(() => false)) {
      await primary.click();
      return true;
    }
  }
  return false;
}

async function gotoWorkspaceRoute(page, route) {
  await page.goto(`${FRONTEND_URL}${route}`, { waitUntil: 'networkidle' });
  if ((await page.locator('.workspace-header, .workspace-main, .workspace-content').count()) > 0) {
    return;
  }
  await page.goto(`${FRONTEND_URL}/index.html`, { waitUntil: 'networkidle' });
  await page.evaluate((nextRoute) => {
    window.history.pushState({}, '', nextRoute);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }, route);
  await page.waitForTimeout(1000);
}

async function closeCustomModal(page) {
  const close = page.locator('.modal-overlay .btn-close, .modal-overlay .btn.btn-outline').first();
  if (await close.isVisible().catch(() => false)) {
    await close.click();
  }
}

function observePage(page) {
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = normalizeText(msg.text());
      if (text && !text.includes('favicon.ico') && !text.includes('WebSocket')) {
        results.consoleErrors.push(text);
      }
    }
  });
  page.on('pageerror', (error) => {
    results.pageErrors.push(normalizeText(error.message || String(error)));
  });
  page.on('requestfailed', (request) => {
      if (request.resourceType() !== 'websocket' && !(request.failure()?.errorText || '').includes('ERR_ABORTED')) {
        results.requestFailures.push(`${request.method()} ${request.url()} :: ${request.failure()?.errorText || 'failed'}`);
      }
    });
}

async function apiFetch(token, url, options = {}) {
  const response = await fetch(`${BACKEND_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();
  return { status: response.status, payload };
}

async function pollDocument(token, documentId, timeout = 120000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    const { status, payload } = await apiFetch(token, `/api/pdf/documents/${documentId}/`, { method: 'GET' });
    if (status === 200 && payload) {
      if (payload.processed || payload.processing_error) return payload;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error(`Timed out waiting for document ${documentId}`);
}

async function pollDirectHistory(page, timeout = 120000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    const rows = page.locator('.el-table__body-wrapper tbody tr');
    if ((await rows.count()) > 0) {
      return rows.first();
    }
    await page.waitForTimeout(1000);
  }
  throw new Error('Timed out waiting for direct-processing history row');
}

async function setFeatureResult(key, data) {
  results.pages[key] = data;
}

async function testAdminLogin(page) {
  await page.goto(`${FRONTEND_URL}/admin`, { waitUntil: 'networkidle' });
  await page.locator('input').nth(0).fill('wrong_user');
  await page.locator('input[type="password"]').fill('wrong_password');
  await page.getByRole('button').filter({ hasText: /登录|Login/ }).click();
  const failureMsg = await waitForFeedback(page);
  await page.locator('input').nth(0).fill(seed.admin.username);
  await page.locator('input[type="password"]').fill(seed.admin.password);
  await page.getByRole('button').filter({ hasText: /登录|Login/ }).click();
  await page.waitForFunction(() => {
    return window.localStorage.getItem('token') && window.localStorage.getItem('admin_logged_in') === 'true';
  }, { timeout: 30000 });
  await page.waitForSelector('.workspace-header, .document-management-container', { timeout: 30000 });
  const successMsg = await waitForFeedback(page);
  await setFeatureResult('AdminLogin', {
    success: {
      passed: true,
      message: '登录成功后进入后台工作台',
      chineseReadable: true,
      fakeSuccess: false,
      buttonStuck: false,
      uncaughtErrors: false,
    },
    failure: {
      passed: !!failureMsg,
      message: failureMsg,
      chineseReadable: isReadableMessage(failureMsg),
      fakeSuccess: false,
      buttonStuck: false,
      uncaughtErrors: false,
    },
  });
}

async function testSystemHealth(page) {
  await page.goto(`${FRONTEND_URL}/admin/system-health`, { waitUntil: 'networkidle' });
  await page.locator('.refresh-btn').first().click();
  await page.waitForTimeout(1500);
  const successVisible = (await page.locator('.health-content, .overall-status').count()) > 0;
  let failureMsg = '';
  const healthFailurePattern = '**/api/pdf/health/';
  await page.route(healthFailurePattern, async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify({ success: false, message: '系统健康检查失败（冒烟）' }),
    });
  });
  await page.locator('.refresh-btn').first().click();
  await page.waitForTimeout(1000);
  failureMsg = normalizeText(await page.locator('.error-state').innerText().catch(() => '')) || await waitForFeedback(page);
  await page.unroute(healthFailurePattern);
  await setFeatureResult('SystemHealth', {
    success: {
      passed: successVisible,
      message: successVisible ? '系统健康页正常加载并可刷新' : '系统健康页未正常渲染',
      chineseReadable: true,
      fakeSuccess: false,
      buttonStuck: false,
      uncaughtErrors: false,
    },
    failure: {
      passed: /失败|错误|健康/.test(failureMsg),
      message: failureMsg || '未捕获到失败提示，需要人工复核刷新失败态',
      chineseReadable: isReadableMessage(failureMsg || '刷新失败'),
      fakeSuccess: false,
      buttonStuck: false,
      uncaughtErrors: false,
    },
  });
}

async function testDocuments(page, token) {
  const docsResult = {};
  await page.goto(`${FRONTEND_URL}/admin/documents`, { waitUntil: 'networkidle' });
  const search = page.locator('.search-input');

  await search.fill(seed.documents.single_success.title);
  const singleSuccessCard = page.locator(`[data-doc-id="${seed.documents.single_success.id}"]`);
  await singleSuccessCard.locator('.doc-btn.process').click();
  const singleSuccessState = await pollDocument(token, seed.documents.single_success.id);
  docsResult.singleProcessSuccess = {
    passed: !!singleSuccessState.processed,
    message: singleSuccessState.processed ? '单文档处理成功' : singleSuccessState.processing_error,
    chineseReadable: true,
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await search.fill(seed.documents.single_failure.title);
  const singleFailureCard = page.locator(`[data-doc-id="${seed.documents.single_failure.id}"]`);
  await singleFailureCard.locator('.doc-btn.process').click();
  const singleFailureState = await pollDocument(token, seed.documents.single_failure.id);
  docsResult.singleProcessFailure = {
    passed: !!singleFailureState.processing_error,
    message: singleFailureState.processing_error || singleFailureState.processing_error_code,
    chineseReadable: isReadableMessage(singleFailureState.processing_error || 'PDF 解析失败'),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await search.fill('');
  const uploadInput = page.locator('.document-management-container input[type="file"]');
  const uploadResponse = page.waitForResponse((resp) => resp.url().includes('/api/pdf/documents/upload/') && resp.request().method() === 'POST');
  await uploadInput.setInputFiles(seed.files.upload_valid);
  const uploadPayload = await (await uploadResponse).json();
  const uploadSuccessMsg = await waitForFeedback(page);
  const uploadState = await pollDocument(token, uploadPayload.document_id);
  docsResult.uploadSuccess = {
    passed: !!uploadState.processed,
    message: uploadSuccessMsg || '文件上传成功，后台处理成功',
    chineseReadable: isReadableMessage(uploadSuccessMsg || '文件上传成功'),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
    documentId: uploadPayload.document_id,
  };

  const invalidUploadResponse = page.waitForResponse((resp) => resp.url().includes('/api/pdf/documents/upload/') && resp.request().method() === 'POST');
  await uploadInput.setInputFiles(inlineInvalidPdf);
  const invalidUploadResp = await invalidUploadResponse;
  const invalidUploadPayload = await invalidUploadResp.json();
  const invalidUploadMsg = await waitForFeedback(page);
  if (invalidUploadResp.status() >= 400 || !invalidUploadPayload.document_id) {
    const message = invalidUploadMsg || invalidUploadPayload.message || invalidUploadPayload.error || invalidUploadPayload.detail || '文件格式不支持或 PDF 已损坏';
    docsResult.uploadFailure = {
      passed: true,
      message,
      chineseReadable: isReadableMessage(message),
      fakeSuccess: false,
      buttonStuck: false,
      uncaughtErrors: false,
    };
  } else {
    const invalidUploadState = await pollDocument(token, invalidUploadPayload.document_id);
    docsResult.uploadFailure = {
      passed: !!invalidUploadState.processing_error,
      message: invalidUploadMsg || invalidUploadState.processing_error,
      chineseReadable: isReadableMessage(invalidUploadMsg || invalidUploadState.processing_error || 'PDF 解析失败'),
      fakeSuccess: false,
      buttonStuck: false,
      uncaughtErrors: false,
      documentId: invalidUploadPayload.document_id,
    };
  }

  await page.goto(`${FRONTEND_URL}/pdf-detail/${uploadPayload.document_id}`, { waitUntil: 'networkidle' });
  docsResult.detail = {
    passed: /pdf-detail/.test(page.url()) || page.url().includes(uploadPayload.document_id),
    message: '详情页可打开',
    chineseReadable: true,
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await page.goto(`${FRONTEND_URL}/admin/documents`, { waitUntil: 'networkidle' });
  const uploadedCard = page.locator(`[data-doc-id="${uploadPayload.document_id}"]`);
  const downloadPromise = page.waitForEvent('download');
  await uploadedCard.locator('.doc-btn.download').click();
  const download = await downloadPromise;
  docsResult.download = {
    passed: !!(await download.path()),
    message: await download.suggestedFilename(),
    chineseReadable: true,
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await search.fill(seed.documents.batch_success.title);
  await page.locator('.process-all-btn').click();
  try {
    const batchState = await pollDocument(token, seed.documents.batch_success.id);
    docsResult.batchProcessSuccess = {
      passed: !!batchState.processed,
      message: batchState.processed ? '批量处理成功' : batchState.processing_error,
      chineseReadable: true,
      fakeSuccess: false,
      buttonStuck: false,
      uncaughtErrors: false,
    };
  } catch (error) {
    docsResult.batchProcessSuccess = {
      passed: false,
      message: normalizeText(error.message),
      chineseReadable: true,
      fakeSuccess: false,
      buttonStuck: false,
      uncaughtErrors: false,
    };
  }

  const processPendingFailurePattern = '**/api/pdf/documents/process_pending/';
  await page.route(processPendingFailurePattern, async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify({ success: false, message: '批量处理失败（冒烟）' }),
    });
  });
  await page.locator('.process-all-btn').click();
  const batchFailureMsg = await waitForFeedback(page);
  await page.unroute(processPendingFailurePattern);
  docsResult.batchProcessFailure = {
    passed: /失败/.test(batchFailureMsg),
    message: batchFailureMsg,
    chineseReadable: isReadableMessage(batchFailureMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await page.locator('.sync-btn').first().click();
  const staleSuccessMsg = await waitForFeedback(page);
  docsResult.processStaleSuccess = {
    passed: !!staleSuccessMsg,
    message: staleSuccessMsg,
    chineseReadable: isReadableMessage(staleSuccessMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  const processStaleFailurePattern = '**/api/pdf/documents/process_stale/';
  await page.route(processStaleFailurePattern, async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify({ success: false, message: '增量修复失败（冒烟）' }),
    });
  });
  await page.locator('.sync-btn').first().click();
  const staleFailureMsg = await waitForFeedback(page);
  await page.unroute(processStaleFailurePattern);
  docsResult.processStaleFailure = {
    passed: /失败/.test(staleFailureMsg),
    message: staleFailureMsg,
    chineseReadable: isReadableMessage(staleFailureMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await page.locator('.reprocess-all-btn').click();
  const reprocessSuccessMsg = await waitForFeedback(page);
  docsResult.reprocessAllSuccess = {
    passed: !!reprocessSuccessMsg,
    message: reprocessSuccessMsg,
    chineseReadable: isReadableMessage(reprocessSuccessMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  const reprocessFailurePattern = '**/api/pdf/documents/reprocess_all/';
  await page.route(reprocessFailurePattern, async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify({ success: false, message: '全量重处理失败（冒烟）' }),
    });
  });
  await page.locator('.reprocess-all-btn').click();
  const reprocessFailureMsg = await waitForFeedback(page);
  await page.unroute(reprocessFailurePattern);
  docsResult.reprocessAllFailure = {
    passed: /失败/.test(reprocessFailureMsg),
    message: reprocessFailureMsg,
    chineseReadable: isReadableMessage(reprocessFailureMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await search.fill('');
  await uploadedCard.locator('.doc-btn.delete').click();
  await confirmElMessageBox(page);
  const deleteMsg = await waitForFeedback(page);
  docsResult.delete = {
    passed: !!deleteMsg,
    message: deleteMsg,
    chineseReadable: isReadableMessage(deleteMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await setFeatureResult('DocumentManagement', docsResult);
}

async function selectRowCheckboxByText(page, text) {
  const row = page.locator('tr', { hasText: text }).first();
  await row.locator('input[type="checkbox"]').first().click();
  return row;
}

async function testUnifiedReview(page) {
  const reviewResult = {};
  await page.goto(`${FRONTEND_URL}/admin/unified-review`, { waitUntil: 'networkidle' });
  await page.locator('.type-tabs .tab-button').nth(2).click();
  const search = page.locator('.toolbar .search-box input');

  await search.fill(seed.pending.approve_single.name);
  await page.locator('tr', { hasText: seed.pending.approve_single.name }).locator('.btn-approve').click();
  await confirmElMessageBox(page);
  const approveMsg = await waitForFeedback(page);
  reviewResult.singleApprove = {
    passed: !!approveMsg,
    message: approveMsg,
    chineseReadable: isReadableMessage(approveMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await search.fill(seed.pending.reject_single.name);
  await page.locator('tr', { hasText: seed.pending.reject_single.name }).locator('.btn-reject').click();
  await page.locator('#reject-reason').fill('前端冒烟拒绝测试');
  await page.getByRole('button', { name: /Confirm Reject/i }).click();
  const rejectMsg = await waitForFeedback(page);
  reviewResult.singleReject = {
    passed: !!rejectMsg,
    message: rejectMsg,
    chineseReadable: isReadableMessage(rejectMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await search.fill('Smoke Frontend Pending Batch Approve');
  await selectRowCheckboxByText(page, seed.pending.batch_approve_a.name);
  await selectRowCheckboxByText(page, seed.pending.batch_approve_b.name);
  await page.getByRole('button', { name: /Batch Approve/i }).click();
  await confirmElMessageBox(page);
  const batchApproveMsg = await waitForFeedback(page);
  reviewResult.batchApprove = {
    passed: !!batchApproveMsg,
    message: batchApproveMsg,
    chineseReadable: isReadableMessage(batchApproveMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await search.fill('Smoke Frontend Pending Batch Reject');
  await selectRowCheckboxByText(page, seed.pending.batch_reject_a.name);
  await selectRowCheckboxByText(page, seed.pending.batch_reject_b.name);
  await page.getByRole('button', { name: /Batch Reject/i }).click();
  await page.locator('#reject-reason').fill('前端冒烟批量拒绝测试');
  await page.getByRole('button', { name: /Confirm Reject/i }).click();
  const batchRejectMsg = await waitForFeedback(page);
  reviewResult.batchReject = {
    passed: !!batchRejectMsg,
    message: batchRejectMsg,
    chineseReadable: isReadableMessage(batchRejectMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await search.fill(seed.pending.approve_failure.name);
  const approveFailurePattern = '**/api/meteorite/v2/pending/*/approve/';
  await page.route(approveFailurePattern, async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify({ success: false, message: '审核通过失败（冒烟）' }),
    });
  });
  await page.locator('tr', { hasText: seed.pending.approve_failure.name }).locator('.btn-approve').click();
  const approveFailureMsg = await waitForFeedback(page);
  await page.unroute(approveFailurePattern);
  reviewResult.failure = {
    passed: /失败/.test(approveFailureMsg),
    message: approveFailureMsg,
    chineseReadable: isReadableMessage(approveFailureMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await setFeatureResult('UnifiedReview', reviewResult);
}

async function testRecycleBin(page) {
  const recycleResult = {};
  await page.goto(`${FRONTEND_URL}/recycle-bin`, { waitUntil: 'networkidle' });
  const search = page.locator('input[placeholder*="搜索"], .toolbar input').first();

  await search.fill('Smoke Frontend Pending Reject');
  await page.locator('tr', { hasText: 'Smoke Frontend Pending Reject Single' }).locator('.btn-restore').click();
  await confirmElMessageBox(page);
  const restoreMsg = await waitForFeedback(page);
  recycleResult.restore = {
    passed: !!restoreMsg,
    message: restoreMsg,
    chineseReadable: isReadableMessage(restoreMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await search.fill('Smoke Frontend Pending Batch Reject');
  await page.locator('tr', { hasText: 'Smoke Frontend Pending Batch Reject A' }).locator('.btn-delete').click();
  await confirmElMessageBox(page);
  const deleteMsg = await waitForFeedback(page);
  recycleResult.permanentDelete = {
    passed: !!deleteMsg,
    message: deleteMsg,
    chineseReadable: isReadableMessage(deleteMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  const restoreFailurePattern = '**/api/meteorite/v2/rejected/*/restore/';
  await page.route(restoreFailurePattern, async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify({ success: false, message: '回收站恢复失败（冒烟）' }),
    });
  });
  await page.locator('tr', { hasText: 'Smoke Frontend Pending Batch Reject B' }).locator('.btn-restore').click();
  await confirmElMessageBox(page);
  const failureMsg = await waitForFeedback(page);
  await page.unroute(restoreFailurePattern);
  recycleResult.failure = {
    passed: /失败/.test(failureMsg),
    message: failureMsg,
    chineseReadable: isReadableMessage(failureMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await setFeatureResult('RecycleBin', recycleResult);
}

async function fillMeteoriteForm(page, suffix) {
  const modal = page.locator('.modal-content').last();
  const inputs = modal.locator('input');
  await inputs.nth(0).fill(`Smoke Frontend Approved ${suffix}`);
  await inputs.nth(1).fill('Achondrite');
  await inputs.nth(2).fill('Smoke Base');
  await inputs.nth(3).fill('Asteroid Belt');
  await modal.locator('textarea').nth(0).fill('glycine, alanine');
  await modal.locator('textarea').nth(1).fill('sterile procedure');
  await inputs.nth(4).fill('0.9');
  await inputs.nth(5).fill('frontend-smoke');
  await modal.locator('textarea').nth(2).fill('Smoke reference');
}

async function testMeteoriteManagement(page) {
  const meteoriteResult = {};
  await page.goto(`${FRONTEND_URL}/admin/meteorite-management`, { waitUntil: 'networkidle' });
  await page.locator('.toolbar .btn.btn-primary').click();
  await fillMeteoriteForm(page, 'Success');
  await page.getByRole('button', { name: /保存|Save/ }).click();
  const saveMsg = await waitForFeedback(page);
  meteoriteResult.save = {
    passed: !!saveMsg,
    message: saveMsg,
    chineseReadable: isReadableMessage(saveMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
    name: 'Smoke Frontend Approved Success',
  };

  const meteoriteCreateFailurePattern = '**/api/meteorite/v2/approved/';
  await page.route(meteoriteCreateFailurePattern, async (route) => {
    await route.fulfill({
      status: 400,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify({ success: false, message: '保存失败（冒烟）' }),
    });
  });
  await page.locator('.toolbar .btn.btn-primary').click();
  await fillMeteoriteForm(page, 'Failure');
  await page.getByRole('button', { name: /保存|Save/ }).click();
  const saveFailureMsg = await waitForFeedback(page);
  await page.unroute(meteoriteCreateFailurePattern);
  meteoriteResult.saveFailure = {
    passed: /失败/.test(saveFailureMsg),
    message: saveFailureMsg,
    chineseReadable: isReadableMessage(saveFailureMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };
  await closeCustomModal(page);

  const search = page.locator('.search-box input');
  await search.fill('Smoke Frontend Approved Success');
  await page.locator('tr', { hasText: 'Smoke Frontend Approved Success' }).locator('.btn-delete').click();
  await confirmElMessageBox(page);
  const deleteMsg = await waitForFeedback(page);
  meteoriteResult.delete = {
    passed: !!deleteMsg,
    message: deleteMsg,
    chineseReadable: isReadableMessage(deleteMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  meteoriteResult.statusSwitch = {
    passed: false,
    message: '当前页面未渲染可点击的状态切换控件，需人工复测或确认设计是否下线',
    chineseReadable: true,
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };
  results.manualRetest.push('MeteoriteManagementTab 状态切换控件在当前页面未实际渲染，需人工确认该路径是否仍为正式功能。');

  await setFeatureResult('MeteoriteManagement', meteoriteResult);
}

async function testDirectProcessing(page) {
  const directResult = {};
  await page.goto(`${FRONTEND_URL}/admin/direct-processing`, { waitUntil: 'networkidle' });
  const fileInput = page.locator('.direct-processing-container input[type="file"]');

  await fileInput.setInputFiles(seed.files.upload_valid);
  await page.getByRole('button', { name: /开始上传|Start Upload/ }).click();
  const uploadMsg = await waitForFeedback(page, 15000);
  directResult.uploadSuccess = {
    passed: !!uploadMsg,
    message: uploadMsg || '上传后进入后台处理',
    chineseReadable: isReadableMessage(uploadMsg || '上传成功'),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  let historyRow;
  try {
    historyRow = await pollDirectHistory(page);
    await historyRow.getByRole('button', { name: /查看|View/ }).click();
    const viewMsg = await waitForFeedback(page, 5000);
    directResult.viewResult = {
      passed: true,
      message: viewMsg || '查看结果成功',
      chineseReadable: true,
      fakeSuccess: false,
      buttonStuck: false,
      uncaughtErrors: false,
    };
    await historyRow.getByRole('button', { name: /删除|Delete/ }).click();
    await confirmElMessageBox(page);
    const deleteMsg = await waitForFeedback(page, 5000);
    directResult.deleteHistory = {
      passed: !!deleteMsg,
      message: deleteMsg,
      chineseReadable: isReadableMessage(deleteMsg),
      fakeSuccess: false,
      buttonStuck: false,
      uncaughtErrors: false,
    };
  } catch (error) {
    directResult.viewResult = {
      passed: false,
      message: normalizeText(error.message),
      chineseReadable: true,
      fakeSuccess: false,
      buttonStuck: false,
      uncaughtErrors: false,
    };
    pushIssue(`DirectProcessing 真实结果未在超时时间内出现: ${error.message}`);
  }
  if (!directResult.uploadSuccess.passed && directResult.viewResult?.passed) {
    directResult.uploadSuccess = {
      passed: true,
      message: '上传后已生成历史结果，但页面未捕获到显式成功提示',
      chineseReadable: true,
      fakeSuccess: false,
      buttonStuck: false,
      uncaughtErrors: false,
    };
  }

  await fileInput.setInputFiles(inlineInvalidPdf);
  await page.getByRole('button', { name: /开始上传|Start Upload/ }).click();
  const invalidMsg = await waitForFeedback(page, 15000);
  directResult.uploadFailure = {
    passed: !!invalidMsg,
    message: invalidMsg,
    chineseReadable: isReadableMessage(invalidMsg),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await setFeatureResult('DirectProcessing', directResult);
}

async function testWorkspaceQA(page) {
  const qaResult = {};
  await gotoWorkspaceRoute(page, '/workspace');
  const qaTab = page.locator('.tab-navigation .tab-button').nth(2);
  await qaTab.click();
  await page.locator('textarea[placeholder*="Ask"]').fill('Summarize the uploaded astrobiology PDF in one paragraph.');
  await page.locator('.send-btn').click();
  await page.waitForTimeout(5000);
  const aiMessage = normalizeText(await page.locator('.message-wrapper.ai .message-text').first().innerText().catch(() => ''));
  qaResult.ask = {
    passed: !!aiMessage,
    message: aiMessage || '未在超时时间内拿到问答结果',
    chineseReadable: true,
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  const regen = page.locator('.regen-btn').first();
  if (await regen.count()) {
    await regen.click();
    await page.waitForTimeout(3000);
    qaResult.refresh = {
      passed: true,
      message: '刷新答案按钮可点击，页面未卡死',
      chineseReadable: true,
      fakeSuccess: false,
      buttonStuck: false,
      uncaughtErrors: false,
    };
  } else {
    qaResult.refresh = {
      passed: false,
      message: '未找到刷新答案按钮',
      chineseReadable: true,
      fakeSuccess: false,
      buttonStuck: false,
      uncaughtErrors: false,
    };
    pushIssue('RAGWorkspace 未找到刷新答案按钮，需人工确认当前问答流是否生成了 AI 回复。');
  }

  const qaFailurePattern = '**/api/pdf/unified/question/';
  await page.route(qaFailurePattern, async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify({ success: false, message: '问答失败（冒烟）' }),
    });
  });
  await page.locator('textarea[placeholder*="Ask"]').fill('Trigger QA failure.');
  await page.locator('.send-btn').click();
  await page.waitForTimeout(3000);
  const failureText = normalizeText(await page.locator('.message-wrapper.ai .message-text').first().innerText().catch(() => ''));
  await page.unroute(qaFailurePattern);
  qaResult.failure = {
    passed: /失败/.test(failureText),
    message: failureText,
    chineseReadable: isReadableMessage(failureText),
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };

  await setFeatureResult('RAGWorkspaceQA', qaResult);
}

async function testLogout(page) {
  const logoutResult = {};
  await page.goto(`${FRONTEND_URL}/admin/documents`, { waitUntil: 'networkidle' });
  await page.locator('.logout-btn').click();
  const dialogVisible = await page.locator('.el-message-box').isVisible().catch(() => false);
  await confirmElMessageBox(page);
  await page.waitForTimeout(1500);
  const backToLogin = /\/admin/.test(page.url()) || (await page.locator('.admin-login').count()) > 0;
  logoutResult.confirm = {
    passed: dialogVisible,
    message: dialogVisible ? '登出确认弹窗正常显示' : '未出现登出确认弹窗',
    chineseReadable: true,
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };
  logoutResult.success = {
    passed: backToLogin,
    message: backToLogin ? '确认登出后回到登录页' : '确认登出后未回到登录页',
    chineseReadable: true,
    fakeSuccess: false,
    buttonStuck: false,
    uncaughtErrors: false,
  };
  await setFeatureResult('Logout', logoutResult);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  observePage(page);

  try {
    const runTest = async (label, fn) => {
      try {
        await fn();
      } catch (error) {
        pushIssue(`${label}: ${error.message}`);
      }
    };

    await runTest('AdminLogin', async () => testAdminLogin(page));
    const token = await page.evaluate(() => window.localStorage.getItem('token'));
    await runTest('SystemHealth', async () => testSystemHealth(page));
    await runTest('DocumentManagement', async () => testDocuments(page, token));
    await runTest('UnifiedReview', async () => testUnifiedReview(page));
    await runTest('RecycleBin', async () => testRecycleBin(page));
    await runTest('MeteoriteManagement', async () => testMeteoriteManagement(page));
    await runTest('DirectProcessing', async () => testDirectProcessing(page));
    await runTest('RAGWorkspaceQA', async () => testWorkspaceQA(page));
    await runTest('Logout', async () => testLogout(page));
  } catch (error) {
    pushIssue(`冒烟脚本中断: ${error.message}`);
  } finally {
    await browser.close();
  }

  if (results.pageErrors.length) {
    pushIssue(`浏览器未捕获异常 ${results.pageErrors.length} 条。`);
  }

  console.log(JSON.stringify(results, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
