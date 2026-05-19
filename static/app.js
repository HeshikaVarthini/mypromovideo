/**
 * VidIntel — frontend
 */

let currentReport = null;

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const MEDALS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"];

document.addEventListener("DOMContentLoaded", () => {
  checkApiHealth();
  $("#report-form").addEventListener("submit", onSubmit);
  $("#download-btn").addEventListener("click", downloadPptx);
  $("#download-btn-bottom").addEventListener("click", downloadPptx);
  $("#new-report-btn").addEventListener("click", resetForm);
});

async function checkApiHealth() {
  const el = $("#api-status");
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.youtube_api_configured) {
      el.textContent = "✓ YouTube API connected — ready to analyse";
      el.className = "api-status ok";
    } else {
      el.textContent = "⚠ YouTube API key not configured on server";
      el.className = "api-status error";
    }
  } catch {
    el.textContent = "Server not reachable";
    el.className = "api-status error";
  }
}

async function onSubmit(e) {
  e.preventDefault();
  const company = $("#company").value.trim();
  const competitors = [...$$(".competitor")].map((i) => i.value.trim()).filter(Boolean);

  if (!company) return showToast("Please enter your company name.");
  if (!competitors.length) return showToast("Please enter at least one competitor.");

  showSection("loading");
  animateLoadingSteps();

  const btn = $("#submit-btn");
  btn.disabled = true;
  $(".btn-text").classList.add("hidden");
  $(".btn-loading").classList.remove("hidden");

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company, competitors }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Analysis failed");

    currentReport = data;
    renderReport(data);
    showSection("report");
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    showToast(err.message || "Something went wrong.");
    showSection("input");
  } finally {
    btn.disabled = false;
    $(".btn-text").classList.remove("hidden");
    $(".btn-loading").classList.add("hidden");
  }
}

function animateLoadingSteps() {
  const steps = ["step-search", "step-videos", "step-analyse"];
  steps.forEach((id, i) => {
    const el = document.getElementById(id);
    el.className = "";
    setTimeout(() => {
      if (i > 0) document.getElementById(steps[i - 1]).className = "done";
      el.className = "active";
    }, i * 3500);
  });
}

function showSection(name) {
  $("#input-section").classList.toggle("hidden", name !== "input");
  $("#loading-section").classList.toggle("hidden", name !== "loading");
  $("#report-section").classList.toggle("hidden", name !== "report");
}

function renderReport(report) {
  const names = [report.company, ...report.competitors];
  $("#report-title").textContent = names.join(" vs ");
  $("#report-date").textContent = `${new Date(report.generated_at).toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric",
  })} · Live YouTube data`;

  $("#executive-summary").textContent = report.executive_summary;
  $("#leader-badge").innerHTML = `
    <strong>Market Leader: ${escapeHtml(report.leader)}</strong>
    <span>${escapeHtml(report.leader_reason)}</span>
  `;

  renderKpis(report);
  renderBarChart("#subscriber-chart", report.comparative_metrics.companies, report.comparative_metrics.subscribers, formatNum);
  renderBarChart("#engagement-chart", report.comparative_metrics.companies, report.comparative_metrics.avg_engagement, (v) => v.toFixed(2) + "%");
  renderRankings(report.rankings);
  renderChannelTable(report.insights, report.channels, report.company);
  renderTopVideos(report.insights);
  renderTopics(report.insights);
  renderEngagementTable(report.insights, report.company);
  renderGaps(report.gap_analysis);
  renderRecommendations(report.recommendations);
}

function renderKpis(report) {
  const grid = $("#kpi-grid");
  const leader = report.rankings[0];
  const userRank = report.rankings.find((r) => r.company_name === report.company);

  grid.innerHTML = `
    <div class="kpi-card highlight">
      <div class="kpi-label">Market Leader</div>
      <div class="kpi-value">${escapeHtml(report.leader)}</div>
      <div class="kpi-sub">Score ${leader ? leader.overall_score.toFixed(0) : "—"}/100</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">${escapeHtml(report.company)} Rank</div>
      <div class="kpi-value">#${userRank ? userRank.rank : "—"}</div>
      <div class="kpi-sub">of ${report.insights.length} brands</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Brands Analysed</div>
      <div class="kpi-value">${report.insights.length}</div>
      <div class="kpi-sub">YouTube channels</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Content Gaps</div>
      <div class="kpi-value">${(report.gap_analysis || []).length}</div>
      <div class="kpi-sub">Opportunities found</div>
    </div>
  `;
}

function renderBarChart(selector, labels, values, formatter) {
  const el = $(selector);
  if (!el || !labels?.length) return;
  const max = Math.max(...values, 1);
  el.innerHTML = labels.map((label, i) => `
    <div class="bar-row">
      <span class="bar-label">${escapeHtml(label)}</span>
      <div class="bar-track"><div class="bar-fill" style="width:0" data-w="${(values[i] / max) * 100}"></div></div>
      <span class="bar-value">${formatter(values[i])}</span>
    </div>
  `).join("");

  requestAnimationFrame(() => {
    el.querySelectorAll(".bar-fill").forEach((bar) => {
      bar.style.width = bar.dataset.w + "%";
    });
  });
}

function renderRankings(rankings) {
  const grid = $("#rankings-grid");
  grid.innerHTML = rankings.map((r, i) => `
    <div class="rank-card rank-${r.rank}">
      <div class="rank-medal">${MEDALS[i] || "#" + r.rank}</div>
      <div class="rank-number">Rank ${r.rank}</div>
      <div class="rank-company">${escapeHtml(r.company_name)}</div>
      <div class="rank-score">${r.overall_score.toFixed(0)}</div>
      <div class="rank-label">Overall Score</div>
      ${scoreBars(r)}
    </div>
  `).join("");
}

function scoreBars(r) {
  const items = [
    ["Audience", r.subscriber_score],
    ["Engagement", r.engagement_score],
    ["Consistency", r.consistency_score],
    ["Volume", r.content_volume_score],
  ];
  return `<div class="score-bar-wrap">${items.map(([label, val]) => `
    <div class="score-bar-label"><span>${label}</span><span>${val.toFixed(0)}</span></div>
    <div class="score-bar"><div class="score-bar-fill" style="width:${val}%"></div></div>
  `).join("")}</div>`;
}

function renderChannelTable(insights, channels, primary) {
  const tbody = $("#channel-table tbody");
  tbody.innerHTML = insights.map((ins) => {
    const ch = channels.find((c) => c.company_name === ins.company_name);
    const hl = ins.company_name === primary ? "highlight-row" : "";
    return `<tr class="${hl}">
      <td><strong>${escapeHtml(ins.company_name)}</strong></td>
      <td>${ch?.channel_url ? `<a href="${ch.channel_url}" target="_blank" rel="noopener">${escapeHtml(ins.channel_title)}</a>` : escapeHtml(ins.channel_title)}</td>
      <td>${formatNum(ins.subscribers)}</td>
      <td>${formatNum(ins.total_videos)}</td>
      <td>${formatNum(ins.total_views)}</td>
      <td>${ins.uploads_per_month.toFixed(1)}</td>
    </tr>`;
  }).join("");
}

function renderTopVideos(insights) {
  $("#top-videos").innerHTML = insights.map((ins) => `
    <div class="company-videos">
      <h4>${escapeHtml(ins.company_name)}</h4>
      <div class="video-cards">
        ${(ins.top_videos || []).slice(0, 3).map((v) => `
          <div class="video-card">
            <img class="video-thumb" src="https://img.youtube.com/vi/${v.video_id}/mqdefault.jpg" alt="" loading="lazy" />
            <div class="video-info">
              <a href="${v.url}" target="_blank" rel="noopener">${escapeHtml(v.title)}</a>
              <div class="video-meta">
                <span class="views">${formatNum(v.views)} views</span>
                <span class="eng">${v.engagement_rate}% eng.</span>
                <span>${formatNum(v.likes)} likes</span>
              </div>
            </div>
          </div>
        `).join("") || "<p>No videos found</p>"}
      </div>
    </div>
  `).join("");
}

function renderTopics(insights) {
  $("#topics-grid").innerHTML = insights.map((ins) => `
    <div class="topic-card">
      <h4>${escapeHtml(ins.company_name)}</h4>
      <div class="topic-tags">
        ${(ins.top_topics || []).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")
          || '<span class="tag">No themes detected</span>'}
      </div>
    </div>
  `).join("");
}

function renderEngagementTable(insights, primary) {
  $("#engagement-table tbody").innerHTML = insights.map((ins) => {
    const hl = ins.company_name === primary ? "highlight-row" : "";
    return `<tr class="${hl}">
      <td><strong>${escapeHtml(ins.company_name)}</strong></td>
      <td>${formatNum(ins.avg_views_per_video)}</td>
      <td>${formatNum(ins.avg_likes_per_video)}</td>
      <td>${formatNum(ins.avg_comments_per_video)}</td>
      <td><strong>${ins.avg_engagement_rate.toFixed(2)}%</strong></td>
      <td>${ins.posting_consistency_score.toFixed(0)}/100</td>
    </tr>`;
  }).join("");
}

function renderGaps(gaps) {
  const list = $("#gap-list");
  if (!gaps?.length) {
    list.innerHTML = "<p style='color:var(--muted)'>No major gaps detected.</p>";
    return;
  }
  list.innerHTML = gaps.map((gap) => `
    <div class="gap-item">
      <h4>${escapeHtml(gap.topic_or_format)}</h4>
      <p class="covered">Covered by: ${escapeHtml(gap.covered_by.join(", "))}</p>
      <p>${escapeHtml(gap.opportunity)}</p>
    </div>
  `).join("");
}

function renderRecommendations(recs) {
  $("#recommendations-list").innerHTML = recs.map((r) => `<li>${escapeHtml(r)}</li>`).join("");
}

async function downloadPptx() {
  if (!currentReport) return showToast("No report to download.");
  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentReport),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Download failed");
    }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `video_intel_${currentReport.company.replace(/\s+/g, "_")}.pptx`;
    a.click();
    showToast("PowerPoint downloaded!", true);
  } catch (err) {
    showToast(err.message || "Download failed");
  }
}

function resetForm() {
  currentReport = null;
  $("#report-form").reset();
  showSection("input");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showToast(msg, ok = false) {
  const t = $("#error-toast");
  t.textContent = msg;
  t.className = ok ? "toast success" : "toast";
  t.classList.remove("hidden");
  setTimeout(() => t.classList.add("hidden"), 5000);
}

function formatNum(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return Number(n).toLocaleString();
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}
