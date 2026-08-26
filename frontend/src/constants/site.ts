/**
 * Dailykyi 站点信息配置。
 * 修改此文件可自定义：作者信息、版权、社交媒体、文档链接等。
 * 文件位置：frontend/src/constants/site.ts
 */

export interface SiteLinks {
  /** 技术博客 / 使用文档：点击"使用文档"跳转到这里 */
  docs: string;
  /** GitHub 仓库地址 */
  github: string;
  /** B 站个人空间地址 */
  bilibili: string;
  /** 作者昵称 */
  authorName: string;
  /** 版权声明（底部显示） */
  copyright: string;
  /** 开源协议 */
  license: string;
  /** 项目版本号 */
  version: string;
  /** 项目 slogan / 副标题 */
  slogan: string;
}

export const SITE: SiteLinks = {
  docs: "https://zzz.3p.chat/",
  github: "https://github.com/Breezets/Dailykyi",
  bilibili: "https://space.bilibili.com/571841739",
  authorName: "微风的铃声",
  copyright: "© 2026 微风的铃声. All rights reserved.",
  license: "MIT License",
  version: "0.1.1",
  slogan: "每日姬 · B 站日常助手",
};
