export type RankedEntry = {
  name: string;
  value: number;
  note?: string;
};

export type StoryCard = {
  name: string;
  value: number;
  label: string;
  summary: string;
};

export type MethodologyNote = {
  label: string;
  value: string;
};

export type SiteStats = {
  summary: {
    totalNonemptyLines: number;
    uniqueFiles: number;
    candidateFiles: number;
    dedupedFilesRemoved: number;
    skillRoots: number;
    binaryFilesSkipped: number;
    repoName: string;
    repoUrl: string;
    roots: string[];
  };
  categories: Array<{
    key: "projects" | "skills";
    title: string;
    value: number;
    blurb: string;
  }>;
  languages: {
    projects: RankedEntry[];
    skills: RankedEntry[];
  };
  topProjects: RankedEntry[];
  topSkills: RankedEntry[];
  flagshipProjects: StoryCard[];
  signatureSkills: StoryCard[];
  methodology: {
    rules: string[];
    excluded: string[];
    validation: MethodologyNote[];
  };
};

export const siteStats: SiteStats = {
  summary: {
    totalNonemptyLines: 80232,
    uniqueFiles: 489,
    candidateFiles: 501,
    dedupedFilesRemoved: 12,
    skillRoots: 73,
    binaryFilesSkipped: 1,
    repoName: "Me-First Warehouse",
    repoUrl: "https://github.com/wjiemin49-ux/Me-First-Warehouse",
    roots: [
      "D:\\me\\脚本",
      "C:\\Users\\MACHENIKE\\.agents\\skills",
      "C:\\Users\\MACHENIKE\\.codex\\skills",
    ],
  },
  categories: [
    {
      key: "projects",
      title: "Projects",
      value: 58335,
      blurb: "以脚本、工具、自动化应用为主，是这座仓库的主发动机。",
    },
    {
      key: "skills",
      title: "Skills",
      value: 21897,
      blurb: "把能力沉淀成可调用的 skill 包，让经验变成可复用工具。",
    },
  ],
  languages: {
    projects: [
      { name: "Python", value: 22115 },
      { name: "TypeScript", value: 14388 },
      { name: "JavaScript", value: 12148 },
      { name: "TSX", value: 5146 },
      { name: "PowerShell", value: 4294 },
      { name: "Batch", value: 172 },
      { name: "C++", value: 37 },
      { name: "C/C++ Header", value: 21 },
      { name: "Rust", value: 14 },
    ],
    skills: [
      { name: "Python", value: 10246 },
      { name: "Markdown", value: 9927 },
      { name: "Shell", value: 1483 },
      { name: "PowerShell", value: 215 },
      { name: "JSON", value: 26 },
    ],
  },
  topProjects: [
    { name: "script-console", value: 30614 },
    { name: "folder-growth-monitor", value: 6414 },
    { name: "sleep-time-recorder", value: 2905 },
    { name: "ai_daily_report", value: 2901 },
    { name: "local-ai-kb", value: 2849 },
    { name: "dev-battle-console", value: 2755 },
    { name: "local-ai-lmstudio", value: 2507 },
    { name: "midnight-self-evolution", value: 2289 },
    { name: "self-growth-daily-briefing", value: 2159 },
    { name: "daily_pc_activity_report", value: 878 },
  ],
  topSkills: [
    { name: "ai-search-hub", value: 2764 },
    { name: "content-collector", value: 2364 },
    { name: "ui-ux-pro-max-0.1.0", value: 1270 },
    { name: "aminer-open-academic-1.0.5", value: 959 },
    { name: "clawdefender-1", value: 918 },
    { name: "wechat-article-formatter", value: 911 },
    { name: "skill-creator", value: 863 },
    { name: "obsidian-ontology-sync-1.0.1", value: 751 },
    { name: "self-improving-agent", value: 716 },
    { name: "wechat-tech-writer", value: 669 },
  ],
  flagshipProjects: [
    {
      name: "script-console",
      value: 30614,
      label: "控制中枢",
      summary: "这是一套本地脚本中控台，把扫描、健康、日志、API 目录、向导和预警系统收进同一个产品外壳里。",
    },
    {
      name: "folder-growth-monitor",
      value: 6414,
      label: "体积雷达",
      summary: "专注目录增长趋势和空间占用异常，让“文件越来越多”这件事变成可视、可控的长期监测。",
    },
    {
      name: "sleep-time-recorder",
      value: 2905,
      label: "生活自动化",
      summary: "把作息记录这种日常问题做成一套可持续运行的小型产品，体现长期主义而不是一次性脚本。",
    },
    {
      name: "ai_daily_report",
      value: 2901,
      label: "信息流编排",
      summary: "把新闻抓取、翻译、汇总和交付串起来，展示从数据获取到成品输出的自动化能力。",
    },
    {
      name: "local-ai-kb",
      value: 2849,
      label: "本地 AI 工具链",
      summary: "围绕本地知识库和 AI 工作流展开，说明这座仓库不只写脚本，也在尝试搭建自己的认知基础设施。",
    },
  ],
  signatureSkills: [
    {
      name: "ai-search-hub",
      value: 2764,
      label: "浏览器作战层",
      summary: "把多站点 AI 搜索和浏览器自动化收敛成可调度技能，适合高频研究与采集场景。",
    },
    {
      name: "content-collector",
      value: 2364,
      label: "内容采集器",
      summary: "从网页、截图到归档和飞书同步，已经不只是说明书，而是带脚本和流程的可执行能力包。",
    },
    {
      name: "ui-ux-pro-max-0.1.0",
      value: 1270,
      label: "界面审美引擎",
      summary: "把视觉方向、交互判断和实现偏好沉淀成技能说明，让设计质量可以被反复复用。",
    },
    {
      name: "aminer-open-academic-1.0.5",
      value: 959,
      label: "学术数据接入",
      summary: "说明能力覆盖面不只在产品和脚本，还延伸到带接口的专业知识查询与分析。",
    },
    {
      name: "clawdefender-1",
      value: 918,
      label: "安全边界",
      summary: "为 agent 工作流补上输入安全与风险审计，体现的是工程习惯，不只是功能堆叠。",
    },
  ],
  methodology: {
    rules: [
      "统计对象覆盖 3 个根路径，统一按非空行计数。",
      "普通项目只统计源码与脚本文件，不把 README、日志、数据文件算进去。",
      "skills 只统计 SKILL.md 与 scripts/ 子树，不把 references、缓存和依赖包算进去。",
      "按归一化文本内容去重，同内容文件只保留一份，优先归属工作区源码。",
      "AI 生成内容没有单独拆类，而是并入对应的 projects 或 skills。",
    ],
    excluded: [
      ".git",
      "node_modules",
      ".venv / .venvs",
      "__pycache__",
      "dist / build / release / out / target",
      "Me-First-Warehouse 镜像目录",
      "_skill_tmp",
      ".tmp-clawhub-vet",
    ],
    validation: [
      { label: "候选文本文件", value: "501 个" },
      { label: "去重后保留", value: "489 个" },
      { label: "移除重复内容", value: "12 个文件" },
      { label: "技能包根目录", value: "73 组" },
      { label: "跳过二进制文件", value: "1 个" },
      { label: "读取失败", value: "0 个" },
    ],
  },
};
