const PAD = (n: number): string => (n < 10 ? `0${n}` : `${n}`);

const TOKENS: Record<string, (d: Date) => string> = {
  YYYY: (d) => `${d.getFullYear()}`,
  MM: (d) => PAD(d.getMonth() + 1),
  DD: (d) => PAD(d.getDate()),
  HH: (d) => PAD(d.getHours()),
  mm: (d) => PAD(d.getMinutes()),
  ss: (d) => PAD(d.getSeconds()),
};

/**
 * 解析 naive datetime 字符串（无时区后缀）的各部分数字。
 * 匹配 "YYYY-MM-DD HH:mm:ss" / "YYYY-MM-DDTHH:mm:ss" / "YYYY-MM-DD HH:mm:ss.ffffff" 等。
 * 直接按字面量切分，不调用 new Date 避免时区转换 bug（Chrome 把无时区 ISO 字符串当 UTC 解析）。
 */
const NAIVE_DATETIME_REGEX =
  /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?$/;

function parseNaiveDateTime(s: string): { year: number; month: number; day: number; hour: number; minute: number; second: number } | null {
  const m = NAIVE_DATETIME_REGEX.exec(s);
  if (!m) return null;
  return {
    year: parseInt(m[1], 10),
    month: parseInt(m[2], 10),
    day: parseInt(m[3], 10),
    hour: parseInt(m[4], 10),
    minute: parseInt(m[5], 10),
    second: parseInt(m[6], 10),
  };
}

/**
 * 简单日期格式化。
 *
 * 重点：后端返回的 created_at 是 naive datetime isoformat（无时区后缀），
 * 数据库实际存的就是本地时间。如果用 new Date(isoString) 解析，
 * Chrome 会按 UTC 解析导致显示偏移 8 小时。
 * 所以这里对 naive datetime 字符串走字面量解析，直接按字面值渲染。
 *
 * @param date  Date 或字符串。字符串优先尝试字面量解析
 * @param fmt   格式串，默认 "YYYY-MM-DD HH:mm:ss"
 */
export function formatDate(
  date: Date | string | number,
  fmt: string = "YYYY-MM-DD HH:mm:ss"
): string {
  // 字符串优先按字面量解析（避免时区转换）
  if (typeof date === "string") {
    const parsed = parseNaiveDateTime(date);
    if (parsed) {
      const literal: Record<string, string> = {
        YYYY: `${parsed.year}`,
        MM: PAD(parsed.month),
        DD: PAD(parsed.day),
        HH: PAD(parsed.hour),
        mm: PAD(parsed.minute),
        ss: PAD(parsed.second),
      };
      let out = fmt;
      for (const [token, val] of Object.entries(literal)) {
        out = out.replace(new RegExp(token, "g"), val);
      }
      return out;
    }
  }

  // fallback：Date 实例 / timestamp / 带时区的 ISO 字符串走 new Date
  const d = date instanceof Date ? date : new Date(date);
  if (Number.isNaN(d.getTime())) return "";
  let out = fmt;
  for (const [token, fn] of Object.entries(TOKENS)) {
    out = out.replace(new RegExp(token, "g"), fn(d));
  }
  return out;
}
