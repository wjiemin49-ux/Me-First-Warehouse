#!/usr/bin/env node

const fs = require("fs");
const fsp = require("fs/promises");
const os = require("os");
const path = require("path");

const OPEN_FEISHU_BASE = "https://open.feishu.cn/open-apis";

function parseArgs(argv) {
  const [command = "smoke", ...rest] = argv;
  const args = { _: [] };

  for (let i = 0; i < rest.length; i += 1) {
    const item = rest[i];
    if (!item.startsWith("--")) {
      args._.push(item);
      continue;
    }

    const key = item.slice(2);
    const next = rest[i + 1];
    if (!next || next.startsWith("--")) {
      args[key] = true;
      continue;
    }

    args[key] = next;
    i += 1;
  }

  return { command, args };
}

function readJsonIfExists(filePath) {
  try {
    if (!fs.existsSync(filePath)) {
      return null;
    }
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    return null;
  }
}

function candidateConfigPaths() {
  const explicit = process.env.FEISHU_CONFIG_PATH;
  const home = os.homedir();
  return [
    explicit,
    path.join(home, ".openclaw-autoclaw", "openclaw.json"),
    path.join(home, ".agents", "skills", "feishu-doc-1.2.7", "config.json"),
    path.join(
      home,
      ".openclaw-autoclaw",
      "workspace",
      ".opencode",
      "skills",
      "feishu-doc-1.2.7",
      "config.json"
    ),
  ].filter(Boolean);
}

function getCredentials() {
  if (process.env.FEISHU_APP_ID && process.env.FEISHU_APP_SECRET) {
    return {
      appId: process.env.FEISHU_APP_ID,
      appSecret: process.env.FEISHU_APP_SECRET,
      source: "environment",
    };
  }

  for (const configPath of candidateConfigPaths()) {
    const config = readJsonIfExists(configPath);
    if (!config) {
      continue;
    }

    const appId =
      config.app_id ||
      config.appId ||
      config.channels?.feishu?.appId ||
      config.channels?.feishu?.accounts?.main?.appId;
    const appSecret =
      config.app_secret ||
      config.appSecret ||
      config.channels?.feishu?.appSecret ||
      config.channels?.feishu?.accounts?.main?.appSecret;

    if (appId && appSecret) {
      return { appId, appSecret, source: configPath };
    }
  }

  throw new Error(
    "Missing Feishu credentials. Set FEISHU_APP_ID / FEISHU_APP_SECRET or FEISHU_CONFIG_PATH."
  );
}

async function parseError(response) {
  const text = await response.text();

  try {
    const json = JSON.parse(text);
    const error = new Error(
      `Feishu API error ${response.status}: ${json.msg || response.statusText}`
    );
    error.status = response.status;
    error.body = json;
    throw error;
  } catch (parseFailure) {
    const error = new Error(`Feishu API error ${response.status}: ${text}`);
    error.status = response.status;
    error.body = text;
    throw error;
  }
}

async function requestJson(url, { method = "GET", accessToken, body } = {}) {
  const headers = {};
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json; charset=utf-8";
  }

  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    await parseError(response);
  }

  const data = await response.json();
  if (typeof data.code === "number" && data.code !== 0) {
    const error = new Error(`Feishu API code ${data.code}: ${data.msg}`);
    error.code = data.code;
    error.body = data;
    throw error;
  }

  return data;
}

async function getTenantAccessToken() {
  const { appId, appSecret, source } = getCredentials();
  const data = await requestJson(
    `${OPEN_FEISHU_BASE}/auth/v3/tenant_access_token/internal`,
    {
      method: "POST",
      body: {
        app_id: appId,
        app_secret: appSecret,
      },
    }
  );

  return {
    token: data.tenant_access_token,
    expire: data.expire,
    credentialSource: source,
  };
}

async function createDoc({ accessToken, title, folderToken }) {
  const body = { title };
  if (folderToken) {
    body.folder_token = folderToken;
  }

  const data = await requestJson(`${OPEN_FEISHU_BASE}/docx/v1/documents`, {
    method: "POST",
    accessToken,
    body,
  });

  const doc = data.data.document;
  return {
    token: doc.document_id,
    title: doc.title,
    revisionId: doc.revision_id,
    url: `https://feishu.cn/docx/${doc.document_id}`,
  };
}

function markdownToBlocks(markdown) {
  const lines = markdown.split(/\r?\n/);
  const blocks = [];

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }

    const makeElements = (content) => [
      {
        text_run: {
          content,
        },
      },
    ];

    if (trimmed.startsWith("### ")) {
      blocks.push({
        block_type: 5,
        heading3: { elements: makeElements(trimmed.slice(4)) },
      });
      continue;
    }

    if (trimmed.startsWith("## ")) {
      blocks.push({
        block_type: 4,
        heading2: { elements: makeElements(trimmed.slice(3)) },
      });
      continue;
    }

    if (trimmed.startsWith("# ")) {
      blocks.push({
        block_type: 3,
        heading1: { elements: makeElements(trimmed.slice(2)) },
      });
      continue;
    }

    if (trimmed.startsWith("- ")) {
      blocks.push({
        block_type: 12,
        bullet: { elements: makeElements(trimmed.slice(2)) },
      });
      continue;
    }

    blocks.push({
      block_type: 2,
      text: { elements: makeElements(line) },
    });
  }

  return blocks;
}

async function appendDoc({ accessToken, docToken, markdown }) {
  const blocks = markdownToBlocks(markdown);
  const data = await requestJson(
    `${OPEN_FEISHU_BASE}/docx/v1/documents/${docToken}/blocks/${docToken}/children`,
    {
      method: "POST",
      accessToken,
      body: {
        children: blocks,
        index: -1,
      },
    }
  );

  return {
    appendedCount: data.data.children.length,
    revisionId: data.data.document_revision_id,
    clientToken: data.data.client_token,
  };
}

async function getDocInfo({ accessToken, docToken }) {
  const data = await requestJson(
    `${OPEN_FEISHU_BASE}/docx/v1/documents/${docToken}`,
    {
      accessToken,
    }
  );

  return data.data.document;
}

function detectMimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const map = {
    ".csv": "text/csv",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".json": "application/json",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".txt": "text/plain",
    ".xlsx":
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  };
  return map[ext] || "application/octet-stream";
}

async function uploadFile({ accessToken, filePath, parentNode, parentType = "explorer" }) {
  const resolvedPath = path.resolve(filePath);
  const stats = await fsp.stat(resolvedPath);
  const buffer = await fsp.readFile(resolvedPath);
  const blob = new Blob([buffer], { type: detectMimeType(resolvedPath) });

  const form = new FormData();
  form.set("file_name", path.basename(resolvedPath));
  form.set("parent_type", parentType);
  form.set("parent_node", parentNode);
  form.set("size", String(stats.size));
  form.set("file", blob, path.basename(resolvedPath));

  const response = await fetch(`${OPEN_FEISHU_BASE}/drive/v1/files/upload_all`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: form,
  });

  if (!response.ok) {
    await parseError(response);
  }

  const data = await response.json();
  if (typeof data.code === "number" && data.code !== 0) {
    const error = new Error(`Feishu API code ${data.code}: ${data.msg}`);
    error.code = data.code;
    error.body = data;
    throw error;
  }

  return data.data.file;
}

async function createFolder({ accessToken, name, parentFolderToken = "root" }) {
  return requestJson(`${OPEN_FEISHU_BASE}/drive/v1/folders`, {
    method: "POST",
    accessToken,
    body: {
      name,
      folder_token: parentFolderToken,
    },
  });
}

function serializeError(error) {
  return {
    message: error.message,
    code: error.code || null,
    status: error.status || null,
    body: error.body || null,
  };
}

function defaultSmokeMarkdown(now) {
  return [
    "# Feishu API smoke test",
    `Run at: ${now.toISOString()}`,
    "",
    "This document was created by a local Node script.",
    "- tenant access token: ok",
    "- doc create: ok",
    "- doc append: ok",
  ].join("\n");
}

async function runSmoke({ folderToken, filePath }) {
  const now = new Date();
  const summary = {
    timestamp: now.toISOString(),
    auth: null,
    folderCreate: null,
    folderDoc: null,
    rootDoc: null,
    upload: null,
  };

  const auth = await getTenantAccessToken();
  const accessToken = auth.token;
  summary.auth = {
    ok: true,
    credentialSource: auth.credentialSource,
    expireSeconds: auth.expire,
  };

  try {
    const folderName = `Codex-Smoke-${now.toISOString().slice(0, 10)}`;
    const folderData = await createFolder({
      accessToken,
      name: folderName,
    });
    summary.folderCreate = {
      ok: true,
      data: folderData.data || folderData,
    };
  } catch (error) {
    summary.folderCreate = {
      ok: false,
      error: serializeError(error),
    };
  }

  const smokeTitle = `Codex Smoke ${now.toISOString().slice(0, 19).replace(/:/g, "-")}`;
  const markdown = defaultSmokeMarkdown(now);

  if (folderToken) {
    try {
      const doc = await createDoc({
        accessToken,
        title: `${smokeTitle} Folder`,
        folderToken,
      });
      const appendResult = await appendDoc({
        accessToken,
        docToken: doc.token,
        markdown,
      });
      summary.folderDoc = {
        ok: true,
        doc,
        appendResult,
      };
    } catch (error) {
      summary.folderDoc = {
        ok: false,
        error: serializeError(error),
      };
    }
  }

  if (!folderToken || (summary.folderDoc && !summary.folderDoc.ok)) {
    try {
      const doc = await createDoc({
        accessToken,
        title: `${smokeTitle} Root`,
      });
      const appendResult = await appendDoc({
        accessToken,
        docToken: doc.token,
        markdown,
      });
      const docInfo = await getDocInfo({
        accessToken,
        docToken: doc.token,
      });
      summary.rootDoc = {
        ok: true,
        doc,
        appendResult,
        docInfo,
      };
    } catch (error) {
      summary.rootDoc = {
        ok: false,
        error: serializeError(error),
      };
    }
  }

  if (filePath && folderToken) {
    try {
      const file = await uploadFile({
        accessToken,
        filePath,
        parentNode: folderToken,
      });
      summary.upload = {
        ok: true,
        file,
      };
    } catch (error) {
      summary.upload = {
        ok: false,
        error: serializeError(error),
      };
    }
  } else if (filePath) {
    summary.upload = {
      ok: false,
      skipped: true,
      reason: "upload_all requires a real folder token; root is not accepted as parent_node.",
    };
  }

  return summary;
}

function requireArg(args, key) {
  if (!args[key]) {
    throw new Error(`Missing required argument --${key}`);
  }
  return args[key];
}

async function main() {
  const { command, args } = parseArgs(process.argv.slice(2));

  if (args.help || args.h) {
    console.log(
      [
        "Usage:",
        "  node feishu/feishu_api.js auth",
        "  node feishu/feishu_api.js create-doc --title \"Smoke\" [--folder-token fld...]",
        "  node feishu/feishu_api.js append-doc --doc-token dox... --content \"# Title\"",
        "  node feishu/feishu_api.js append-doc --doc-token dox... --content-file ./note.md",
        "  node feishu/feishu_api.js upload-file --file ./demo.png --parent-node fld...",
        "  node feishu/feishu_api.js smoke [--folder-token fld...] [--file ./demo.png]",
      ].join("\n")
    );
    return;
  }

  switch (command) {
    case "auth": {
      const result = await getTenantAccessToken();
      console.log(
        JSON.stringify(
          {
            ok: true,
            credentialSource: result.credentialSource,
            expireSeconds: result.expire,
          },
          null,
          2
        )
      );
      return;
    }

    case "create-doc": {
      const auth = await getTenantAccessToken();
      const result = await createDoc({
        accessToken: auth.token,
        title: requireArg(args, "title"),
        folderToken: args["folder-token"],
      });
      console.log(JSON.stringify(result, null, 2));
      return;
    }

    case "append-doc": {
      const auth = await getTenantAccessToken();
      const docToken = requireArg(args, "doc-token");
      let content = args.content;

      if (args["content-file"]) {
        content = await fsp.readFile(path.resolve(args["content-file"]), "utf8");
      }

      if (!content) {
        throw new Error("Provide --content or --content-file.");
      }

      const result = await appendDoc({
        accessToken: auth.token,
        docToken,
        markdown: content,
      });
      console.log(JSON.stringify(result, null, 2));
      return;
    }

    case "upload-file": {
      const auth = await getTenantAccessToken();
      const result = await uploadFile({
        accessToken: auth.token,
        filePath: requireArg(args, "file"),
        parentNode: requireArg(args, "parent-node"),
        parentType: args["parent-type"] || "explorer",
      });
      console.log(JSON.stringify(result, null, 2));
      return;
    }

    case "smoke": {
      const result = await runSmoke({
        folderToken: args["folder-token"],
        filePath: args.file,
      });
      console.log(JSON.stringify(result, null, 2));
      return;
    }

    default:
      throw new Error(`Unknown command: ${command}`);
  }
}

main().catch((error) => {
  console.error(
    JSON.stringify(
      {
        ok: false,
        error: serializeError(error),
      },
      null,
      2
    )
  );
  process.exitCode = 1;
});
