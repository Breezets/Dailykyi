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
 * 简单日期格式化。
 * @param date  Date 或可被 new Date() 解析的字符串
 * @param fmt   格式串，默认 "YYYY-MM-DD HH:mm:ss"
 */
export function formatDate(
  date: Date | string | number,
  fmt: string = "YYYY-MM-DD HH:mm:ss"
): string {
  const d = date instanceof Date ? date : new Date(date);
  if (Number.isNaN(d.getTime())) return "";
  let out = fmt;
  for (const [token, fn] of Object.entries(TOKENS)) {
    out = out.replace(new RegExp(token, "g"), fn(d));
  }
  return out;
}
