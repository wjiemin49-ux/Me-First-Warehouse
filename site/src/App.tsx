import "./styles.css";
import { siteStats, type RankedEntry, type StoryCard } from "./data/stats";

const numberFormatter = new Intl.NumberFormat("zh-CN");

function formatNumber(value: number) {
  return numberFormatter.format(value);
}

function formatPercent(value: number, total: number) {
  return `${((value / total) * 100).toFixed(1)}%`;
}

function SectionHeading(props: {
  id: string;
  eyebrow: string;
  title: string;
  lede: string;
}) {
  return (
    <div className="section-heading" id={props.id}>
      <p className="eyebrow">{props.eyebrow}</p>
      <h2>{props.title}</h2>
      <p className="section-lede">{props.lede}</p>
    </div>
  );
}

function HeroStat(props: {
  label: string;
  value: number;
  detail: string;
  delay: number;
}) {
  return (
    <article
      className="hero-stat reveal-card"
      style={{ animationDelay: `${props.delay}ms` }}
    >
      <p className="hero-stat-label">{props.label}</p>
      <strong>{formatNumber(props.value)}</strong>
      <span>{props.detail}</span>
    </article>
  );
}

function CategoryCard(props: {
  title: string;
  value: number;
  total: number;
  blurb: string;
  tone: "warm" | "cool";
}) {
  return (
    <article className={`category-card ${props.tone}`}>
      <p className="eyebrow">{props.title}</p>
      <strong>{formatNumber(props.value)}</strong>
      <span>{formatPercent(props.value, props.total)}</span>
      <p>{props.blurb}</p>
    </article>
  );
}

function RankedBars(props: {
  items: RankedEntry[];
  total: number;
  unit: string;
}) {
  return (
    <div className="bar-list">
      {props.items.map((item, index) => (
        <div className="bar-row" key={item.name}>
          <div className="bar-copy">
            <span className="bar-rank">{String(index + 1).padStart(2, "0")}</span>
            <div>
              <strong>{item.name}</strong>
              {item.note ? <p>{item.note}</p> : null}
            </div>
          </div>
          <div className="bar-meter">
            <div
              className="bar-meter-fill"
              style={{ width: `${(item.value / props.total) * 100}%` }}
            />
          </div>
          <span className="bar-value">
            {formatNumber(item.value)}
            {props.unit}
          </span>
        </div>
      ))}
    </div>
  );
}

function StoryGrid(props: { items: StoryCard[]; accent: "ember" | "teal" }) {
  return (
    <div className="story-grid">
      {props.items.map((item, index) => (
        <article
          className={`story-card ${props.accent}`}
          key={item.name}
          style={{ animationDelay: `${index * 90}ms` }}
        >
          <div className="story-meta">
            <span>{item.label}</span>
            <strong>{formatNumber(item.value)} 行</strong>
          </div>
          <h3>{item.name}</h3>
          <p>{item.summary}</p>
        </article>
      ))}
    </div>
  );
}

export default function App() {
  const total = siteStats.summary.totalNonemptyLines;
  const projectCategory = siteStats.categories.find(
    (entry) => entry.key === "projects",
  );
  const skillCategory = siteStats.categories.find((entry) => entry.key === "skills");

  if (!projectCategory || !skillCategory) {
    return null;
  }

  return (
    <div className="site-shell">
      <div className="ambient ambient-one" aria-hidden="true" />
      <div className="ambient ambient-two" aria-hidden="true" />

      <header className="topbar">
        <a className="brand" href="#hero">
          <span className="brand-mark">MW</span>
          <span className="brand-copy">
            <strong>{siteStats.summary.repoName}</strong>
            <small>代码统计总结站</small>
          </span>
        </a>

        <nav className="anchor-nav" aria-label="页面导航">
          <a href="#overview">总览</a>
          <a href="#composition">结构</a>
          <a href="#projects">项目</a>
          <a href="#skills">Skills</a>
          <a href="#methodology">方法</a>
        </nav>

        <a
          className="ghost-link"
          href={siteStats.summary.repoUrl}
          target="_blank"
          rel="noreferrer"
        >
          查看 GitHub
        </a>
      </header>

      <main>
        <section className="hero" id="hero">
          <div className="hero-copy">
            <p className="eyebrow">Code Census / Spring 2026</p>
            <h1>80,232 行非空代码，拼出一个持续运转的个人自动化仓。</h1>
            <p className="hero-lede">
              这不是一个单独项目，而是一整座围绕脚本、skills、本地 AI 工具链和实验产品展开的个人代码宇宙。
              它同时追求能跑、能用、能复用，也在缓慢形成属于自己的方法论。
            </p>

            <div className="hero-actions">
              <a className="primary-link" href="#composition">
                看结构分布
              </a>
              <a className="secondary-link" href="#projects">
                进入头部项目
              </a>
            </div>

            <div className="scope-pills">
              {siteStats.summary.roots.map((root) => (
                <span key={root}>{root}</span>
              ))}
            </div>
          </div>

          <aside className="hero-panel reveal-card">
            <p className="panel-kicker">核心事实</p>
            <div className="hero-grid">
              <HeroStat
                label="总代码量"
                value={siteStats.summary.totalNonemptyLines}
                detail="按非空行统计"
                delay={80}
              />
              <HeroStat
                label="Projects"
                value={projectCategory.value}
                detail="脚本、工具、产品化项目"
                delay={160}
              />
              <HeroStat
                label="Skills"
                value={skillCategory.value}
                detail="技能包与脚本沉淀"
                delay={240}
              />
              <HeroStat
                label="唯一文件"
                value={siteStats.summary.uniqueFiles}
                detail="去重后保留"
                delay={320}
              />
            </div>

            <div className="hero-footnotes">
              <span>去掉重复内容 {formatNumber(siteStats.summary.dedupedFilesRemoved)} 个文件</span>
              <span>覆盖 {formatNumber(siteStats.summary.skillRoots)} 组 skills 根目录</span>
              <span>读取失败 0 个文件</span>
            </div>
          </aside>
        </section>

        <section className="section" id="overview">
          <SectionHeading
            id="overview-heading"
            eyebrow="Narrative Summary"
            title="这份统计更像一张工作方法地图，而不只是数字汇总。"
            lede="它同时暴露了体量、偏好和产出节奏。大体量项目说明你在做长期产品，skills 说明你在把经验压缩成可重复调用的能力模块。"
          />

          <div className="narrative-layout">
            <div className="narrative-copy">
              <p>
                从结构上看，这座仓库的主引擎是 <strong>Projects</strong>。它们承担真实运行逻辑，
                包括本地控制台、目录增长监控、作息记录、日报流水线和本地 AI
                基础设施。这部分占据了整体代码量的大头，也说明你不是停留在零散脚本，而是在反复把工具做成产品。
              </p>
              <p>
                与之并行的是 <strong>Skills</strong>。它们不只是提示词，而是带有
                `SKILL.md`、脚本、自动化入口和执行边界的能力封装。换句话说，这里积累的不只是功能，还有方法。每次把一个技能包写清楚，都是在把个人经验变成未来可调度的资产。
              </p>
              <p>
                对外来看，这份站点想表达的不是“我写了很多代码”，而是“我已经在持续构建一个能自我增强、能扩展、能服务真实工作流的仓库系统”。
                代码量只是痕迹，真正有分量的是它背后的结构感。
              </p>
            </div>

            <div className="pull-quote">
              <p>
                “从脚本到技能包，再到可运行产品，Me-First Warehouse
                更像一座不断扩建的个人软件工坊。”
              </p>
            </div>
          </div>
        </section>

        <section className="section" id="composition">
          <SectionHeading
            id="composition-heading"
            eyebrow="Category Split"
            title="Projects 是主引擎，Skills 是方法层。"
            lede="两类内容分工明确，一类负责跑起来，一类负责沉淀下来。把它们放在一起看，能更清楚地看到这座仓库为什么会持续增长。"
          />

          <div className="category-layout">
            <CategoryCard
              title={projectCategory.title}
              value={projectCategory.value}
              total={total}
              blurb={projectCategory.blurb}
              tone="warm"
            />
            <CategoryCard
              title={skillCategory.title}
              value={skillCategory.value}
              total={total}
              blurb={skillCategory.blurb}
              tone="cool"
            />
          </div>

          <div className="chart-grid">
            <article className="panel-card">
              <div className="panel-head">
                <p className="eyebrow">Language Footprint / Projects</p>
                <h3>项目类语言分布</h3>
              </div>
              <RankedBars items={siteStats.languages.projects} total={projectCategory.value} unit=" 行" />
            </article>

            <article className="panel-card">
              <div className="panel-head">
                <p className="eyebrow">Language Footprint / Skills</p>
                <h3>Skills 语言分布</h3>
              </div>
              <RankedBars items={siteStats.languages.skills} total={skillCategory.value} unit=" 行" />
            </article>
          </div>
        </section>

        <section className="section" id="projects">
          <SectionHeading
            id="projects-heading"
            eyebrow="Flagship Projects"
            title="头部项目让这座仓库从脚本集合变成了产品矩阵。"
            lede="下面这些项目占据了主要体量，也最能体现你的产品意识、自动化方向和长期维护能力。"
          />

          <StoryGrid items={siteStats.flagshipProjects} accent="ember" />

          <article className="panel-card ranking-card">
            <div className="panel-head">
              <p className="eyebrow">Top 10 / Projects</p>
              <h3>项目榜单</h3>
            </div>
            <RankedBars items={siteStats.topProjects} total={siteStats.topProjects[0].value} unit=" 行" />
          </article>
        </section>

        <section className="section" id="skills">
          <SectionHeading
            id="skills-heading"
            eyebrow="Skills Constellation"
            title="Skills 像一张星图，把零散经验变成可调用能力。"
            lede="它们覆盖浏览器自动化、内容采集、界面设计、学术数据、安全和 agent 工作流，展示的是横向广度与可复用意识。"
          />

          <StoryGrid items={siteStats.signatureSkills} accent="teal" />

          <article className="panel-card ranking-card">
            <div className="panel-head">
              <p className="eyebrow">Top 10 / Skills</p>
              <h3>Skill 榜单</h3>
            </div>
            <RankedBars items={siteStats.topSkills} total={siteStats.topSkills[0].value} unit=" 行" />
          </article>
        </section>

        <section className="section" id="methodology">
          <SectionHeading
            id="methodology-heading"
            eyebrow="Methodology / Notes"
            title="数字背后，统计口径同样重要。"
            lede="这份站点没有追求“把一切都算进去”，而是尽量把真正属于工作成果的文本代码挑出来，减少依赖、缓存和镜像副本造成的噪音。"
          />

          <div className="method-layout">
            <article className="panel-card">
              <div className="panel-head">
                <p className="eyebrow">Counting Rules</p>
                <h3>统计规则</h3>
              </div>
              <ul className="note-list">
                {siteStats.methodology.rules.map((rule) => (
                  <li key={rule}>{rule}</li>
                ))}
              </ul>
            </article>

            <article className="panel-card">
              <div className="panel-head">
                <p className="eyebrow">Excluded Noise</p>
                <h3>主动排除的噪音</h3>
              </div>
              <ul className="tag-list">
                {siteStats.methodology.excluded.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          </div>

          <article className="panel-card validation-card">
            <div className="panel-head">
              <p className="eyebrow">Validation Snapshot</p>
              <h3>校验摘要</h3>
            </div>
            <div className="validation-grid">
              {siteStats.methodology.validation.map((item) => (
                <div className="validation-item" key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </div>
              ))}
            </div>
            <details className="method-details">
              <summary>展开查看说明</summary>
              <p>
                这次统计按非空行计数，普通项目只收源码和脚本，skills 只收
                `SKILL.md` 与 `scripts/`，并对归一化文本内容做去重。最终保留
                {` ${formatNumber(siteStats.summary.uniqueFiles)} `}
                个唯一文件，移除了
                {` ${formatNumber(siteStats.summary.dedupedFilesRemoved)} `}
                个重复文件，另外还跳过了
                {` ${formatNumber(siteStats.summary.binaryFilesSkipped)} `}
                个二进制文件。AI 生成内容没有单独拆类，而是并入所属项目或 skill。
              </p>
            </details>
          </article>
        </section>
      </main>

      <footer className="footer">
        <div>
          <p className="eyebrow">Closing CTA</p>
          <h2>如果你想看一个人如何把脚本、技能包和工具链慢慢做成体系，这就是一张缩略地图。</h2>
          <p>
            这份站点展示的是当前切片，而不是终点。仓库还会继续长，skills 还会继续分化，
            但今天已经能看见一个明确趋势：个人自动化，正在变成个人基础设施。
          </p>
        </div>

        <a
          className="primary-link footer-link"
          href={siteStats.summary.repoUrl}
          target="_blank"
          rel="noreferrer"
        >
          前往 GitHub 仓库
        </a>
      </footer>
    </div>
  );
}
