import { readFile } from "node:fs/promises";

/**
 * 轻量 JSON Schema 子集校验器（零依赖，供测试与发布脚本共用）。
 *
 * 支持的关键字：$ref（本文件 definitions）、type（字符串或数组，含 "null"）、
 * enum、required、properties、items、additionalProperties（bool 或 schema）、
 * minimum / maximum / minLength / minItems。
 * 不支持的关键字一律忽略（本目录 schema 也不用 allOf）——schema 必须配合
 * 「禁止字段扫描」使用（见 scanForbidden）。
 */

export class ValidationError extends Error {
  constructor(errors) {
    super("schema 校验失败:\n" + errors.map((e) => `  ${e.path}: ${e.message}`).join("\n"));
    this.name = "ValidationError";
    this.errors = errors;
  }
}

/** 公开工件禁止出现的字段名（评测文档 §12 / showcase 文档 §13.4）。 */
export const FORBIDDEN_KEYS = [
  "system_prompt", "systemprompt", "api_key", "apikey", "authorization",
  "x-internal-token", "password", "secret", "cookie", "session_token",
];

/** 深度扫描序列化文本中的禁止字段名（大小写不敏感）。 */
export function scanForbidden(value) {
  const text = JSON.stringify(value) || "";
  const hits = FORBIDDEN_KEYS.filter((key) => new RegExp(`"${key}"\\s*:`, "i").test(text));
  return hits;
}

export async function loadSchema(name) {
  const raw = await readFile(new URL(`./showcase-data/${name}.schema.json`, import.meta.url), "utf8");
  return JSON.parse(raw);
}

export function validate(payload, schema) {
  const errors = [];
  walk(payload, schema, schema, "$", errors);
  if (errors.length > 0) throw new ValidationError(errors);
}

function resolveRef(schema, root, ref) {
  if (!ref || !ref.startsWith("#/")) return schema;
  let node = root;
  for (const part of ref.slice(2).split("/")) node = node[part];
  return node;
}

function typeMatches(value, type) {
  if (Array.isArray(type)) return type.some((t) => typeMatches(value, t));
  switch (type) {
    case "null": return value === null;
    case "boolean": return typeof value === "boolean";
    case "string": return typeof value === "string";
    case "integer": return Number.isInteger(value);
    case "number": return typeof value === "number" && Number.isFinite(value);
    case "array": return Array.isArray(value);
    case "object": return typeof value === "object" && value !== null && !Array.isArray(value);
    default: return true;
  }
}

function walk(value, schema, root, path, errors) {
  if (!schema || typeof schema !== "object") return;
  if (schema.$ref) {
    walk(value, resolveRef(schema, root, schema.$ref), root, path, errors);
    return;
  }
  if (schema.type !== undefined && !typeMatches(value, schema.type)) {
    errors.push({ path, message: `类型应为 ${JSON.stringify(schema.type)}，实际 ${describe(value)}` });
    return;
  }
  if (schema.enum !== undefined && !schema.enum.some((item) => equals(item, value))) {
    errors.push({ path, message: `值 ${JSON.stringify(value)} 不在枚举 ${JSON.stringify(schema.enum)}` });
  }
  if (typeof value === "number") {
    if (schema.minimum !== undefined && value < schema.minimum) {
      errors.push({ path, message: `${value} < 最小值 ${schema.minimum}` });
    }
    if (schema.maximum !== undefined && value > schema.maximum) {
      errors.push({ path, message: `${value} > 最大值 ${schema.maximum}` });
    }
  }
  if (typeof value === "string" && schema.minLength !== undefined && value.length < schema.minLength) {
    errors.push({ path, message: `字符串长度 ${value.length} < ${schema.minLength}` });
  }
  if (Array.isArray(value)) {
    if (schema.minItems !== undefined && value.length < schema.minItems) {
      errors.push({ path, message: `数组元素数 ${value.length} < ${schema.minItems}` });
    }
    if (schema.items) {
      value.forEach((item, index) => walk(item, schema.items, root, `${path}[${index}]`, errors));
    }
  }
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    for (const key of schema.required || []) {
      if (!(key in value)) errors.push({ path, message: `缺少必填字段 "${key}"` });
    }
    if (schema.properties) {
      for (const [key, sub] of Object.entries(schema.properties)) {
        if (key in value) walk(value[key], sub, root, `${path}.${key}`, errors);
      }
    }
    if (schema.additionalProperties === false) {
      const known = new Set([...Object.keys(schema.properties || {}), ...(schema.required || [])]);
      for (const key of Object.keys(value)) {
        if (!known.has(key)) errors.push({ path, message: `未知字段 "${key}"（additionalProperties: false）` });
      }
    } else if (schema.additionalProperties && typeof schema.additionalProperties === "object") {
      for (const [key, sub] of Object.entries(value)) {
        if (!(schema.properties || {})[key]) walk(value[key], schema.additionalProperties, root, `${path}.${key}`, errors);
      }
    }
  }
}

function equals(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

function describe(value) {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value;
}
