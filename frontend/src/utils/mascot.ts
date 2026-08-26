/**
 * 2233 吉祥物图片工具。
 *
 * 图片目录：frontend/public/mascots/
 *  - 01.png ~ 09.png       : 1:1 方图，用于侧边栏小图轮播
 *  - homephoto/home-01.* ~ home-18.* : 多比例横图，用于首页横幅
 *
 * 替换图片：直接覆盖同名文件即可，无需改代码或重新构建。
 */

// ============= 侧边栏小图（1:1 方图）=============
const SIDEBAR_MASCOT_COUNT = 9;

export function getSidebarMascotByIndex(index: number): string {
  const i = ((index - 1) % SIDEBAR_MASCOT_COUNT + SIDEBAR_MASCOT_COUNT) % SIDEBAR_MASCOT_COUNT + 1;
  return `/mascots/${String(i).padStart(2, "0")}.png`;
}

export function getAllSidebarMascots(): string[] {
  return Array.from({ length: SIDEBAR_MASCOT_COUNT }, (_, i) => getSidebarMascotByIndex(i + 1));
}

// ============= 首页横幅图（多比例）=============
// homephoto 目录下的图片长宽比不一，文件名: home-01 ~ home-18
// 使用时通过 object-fit: cover 自适应裁剪显示

const HOME_MASCOT_FILES: string[] = [
  "home-01.png",
  "home-02.jpg",
  "home-03.png",
  "home-04.png",
  "home-05.jpg",
  "home-06.jpg",
  "home-07.jpg",
  "home-08.jpg",
  "home-09.jpg",
  "home-10.png",
  "home-11.jpg",
  "home-12.jpg",
  "home-13.jpg",
  "home-14.jpg",
  "home-15.jpg",
  "home-16.jpg",
  "home-17.png",
  "home-18.jpg",
];

export function getHomeMascotByIndex(index: number): string {
  const n = HOME_MASCOT_FILES.length;
  const i = ((index - 1) % n + n) % n;
  return `/mascots/homephoto/${HOME_MASCOT_FILES[i]}`;
}

export function getAllHomeMascots(): string[] {
  return HOME_MASCOT_FILES.map((f) => `/mascots/homephoto/${f}`);
}

/** 根据当天日期选一张首页图（同一天同一张） */
export function getDailyHomeMascot(): string {
  const now = new Date();
  const dayOfYear = Math.floor(
    (now.getTime() - new Date(now.getFullYear(), 0, 0).getTime()) / 86400000
  );
  return getHomeMascotByIndex(dayOfYear + 1);
}

// ============= 向后兼容（已废弃，保留以免破坏旧引用）=============
/** @deprecated 使用 getSidebarMascotByIndex 代替 */
export function getMascotByIndex(index: number): string {
  return getSidebarMascotByIndex(index);
}
/** @deprecated 使用 getDailyHomeMascot 代替 */
export function getDailyMascot(): string {
  return getDailyHomeMascot();
}
/** @deprecated 使用 getAllSidebarMascots 代替 */
export function getAllMascots(): string[] {
  return getAllSidebarMascots();
}
