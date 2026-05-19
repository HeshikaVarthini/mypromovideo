/**
 * Video Competitor Intelligence — frontend
 */

let currentReport = null;

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

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
  const competitors = [...$$(".competitor")]
    .map((inp) => inp.value.trim())
    .filter(Boolean);

  if (!company) {
    showToast("Please enter your company name.");
    return;
  }
  if (competitors.length === 0) {
    showToast("Please enter at least one competitor.");
    return;
  }

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
    if (!res.ok) {
      throw new Error(data.detail || "Analysis failed");
    }

    currentReport = data;
    renderReport(data);
    showSection("report");
  } catch (err) {
    showToast(err.message || "Something went wrong. Please try again.");
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
    }, i * 4000);
  });
  setTimeout(() => {
    steps.forEach((id) => {
      document.getElementById(id).className = "done";
    });
  }, 12000);
}

function showSection(name) {
  $("#input-section").classList.toggle("hidden", name !== "input");
  $("#loading-section").classList.toggle("hidden", name !== "loading");
  $("#report-section").classList.toggle("hidden", name !== "report");
}

function renderReport(report) {
  const names = [report.company, ...report.competitors];
  $("#report-title").textContent = `Report: ${names.join(" vs ")}`;
  const date = new Date(report.generated_at).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  $("#report-date").textContent = `Generated ${date} · Based on live YouTube data`;

  $("#executive-summary").textContent = report.executive_summary;
  $("#leader-badge").innerHTML = `
    <strong>🏆 Market Leader: ${escapeHtml(report.leader)}</strong>
    ${escapeHtml(report.leader_reason)}
  `;

  renderChannelTable(report.insights, report.channels);
  renderRankings(report.rankings);
  renderTopVideos(report.insights);
  renderTopics(report.insights);
  renderEngagementTable(report.insights);
  renderGaps(report.gap_analysis);
  renderRecommendations(report.recommendations);
}

function renderChannelTable(insights, channels) {
  const tbody = $("#channel-table tbody");
  tbody.innerHTML = "";
  insights.forEach((ins) => {
    const ch = channels.find((c) => c.company_name === ins.company_name);
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${escapeHtml(ins.company_name)}</strong></td>
      <td>${ch && ch.channel_url ? `<a href="${ch.channel_url}" target="_blank" rel="noopener">${escapeHtml(ins.channel_title)}</a>` : escapeHtml(ins.channel_title)}</td>
      <td>${formatNum(ins.subscribers)}</td>
      <td>${formatNum(ins.total_videos)}</td>
      <td>${formatNum(ins.total_views)}</td>
      <td>${ins.uploads_per_month.toFixed(1)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderRankings(rankings) {
  const grid = $("#rankings-grid");
  grid.innerHTML = "";
  rankings.forEach((r) => {
    const card = document.createElement("div");
    card.className = `rank-card rank-${r.rank}`;
    card.innerHTML = `
      <div class="rank-number">#${r.rank}</div>
      <div class="rank-company">${escapeHtml(r.company_name)}</div>
      <div class="rank-score">${r.overall_score.toFixed(0)}</div>
      <div class="rank-label">Overall Score / 100</div>
      <div class="rank-breakdown">
        Audience: ${r.subscriber_score.toFixed(0)} ·
        Engagement: ${r.engagement_score.toFixed(0)} ·
        Consistency: ${r.consistency_score.toFixed(0)} ·
        Volume: ${r.content_volume_score.toFixed(0)}
      </div>
    `;
    grid.appendChild(card);
  });
}

function renderTopVideos(insights) {
  const container = $("#top-videos");
  container.innerHTML = "";
  insights.forEach((ins) => {
    const section = document.createElement("div");
    section.className = "company-section";
    const videos = (ins.top_videos || [])
      .map(
        (v) => `
      <li>
        <a href="${v.url}" target="_blank" rel="noopener">${escapeHtml(v.title)}</a>
        <div class="video-stats">${formatNum(v.views)} views · ${v.engagement_rate}% engagement · ${formatNum(v.likes)} likes</div>
      </li>
    `
      )
      .join("");
    section.innerHTML = `
      <h4>${escapeHtml(ins.company_name)}</h4>
      <ul class="video-list">${videos || "<li>No video data</li>"}</ul>
    `;
    container.appendChild(section);
  });
}

function renderTopics(insights) {
  const grid = $("#topics-grid");
  grid.innerHTML = "";
  insights.forEach((ins) => {
    const card = document.createElement("div");
    card.className = "topic-card";
    const tags = (ins.top_topics || [])
      .map((t) => `<span class="tag">${escapeHtml(t)}</span>`)
      .join("");
    card.innerHTML = `
      <h4>${escapeHtml(ins.company_name)}</h4>
      <div class="topic-tags">${tags || '<span class="tag">No themes detected</span>'}</div>
    `;
    grid.appendChild(card);
  });
}

function renderEngagementTable(insights) {
  const tbody = $("#engagement-table tbody");
  tbody.innerHTML = "";
  insights.forEach((ins) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${escapeHtml(ins.company_name)}</strong></td>
      <td>${formatNum(ins.avg_views_per_video)}</td>
      <td>${formatNum(ins.avg_likes_per_video)}</td>
      <td>${formatNum(ins.avg_comments_per_video)}</td>
      <td>${ins.avg_engagement_rate.toFixed(2)}%</td>
      <td>${ins.posting_consistency_score.toFixed(0)}/100</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderGaps(gaps) {
  const list = $("#gap-list");
  list.innerHTML = "";
  if (!gaps || gaps.length === 0) {
    list.innerHTML = "<p>No significant gaps detected in this competitive set.</p>";
    return;
  }
  gaps.forEach((gap) => {
    const div = document.createElement("div");
    div.className = "gap-item";
    div.innerHTML = `
      <h4>${escapeHtml(gap.topic_or_format)}</h4>
      <p><strong>Covered by:</strong> ${escapeHtml(gap.covered_by.join(", "))}</p>
      <p>${escapeHtml(gap.opportunity)}</p>
    `;
    list.appendChild(div);
  });
}

function renderRecommendations(recs) {
  const ol = $("#recommendations-list");
  ol.innerHTML = "";
  recs.forEach((rec) => {
    const li = document.createElement("li");
    li.textContent = rec;
    ol.appendChild(li);
  });
}

async function downloadPptx() {
  if (!currentReport) {
    showToast("No report to download.");
    return;
  }
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
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `video_intel_${currentReport.company.replace(/\s+/g, "_")}.pptx`;
    a.click();
    URL.revokeObjectURL(url);
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

function showToast(msg, success = false) {
  const toast = $("#error-toast");
  toast.textContent = msg;
  toast.className = success ? "toast success" : "toast";
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 5000);
}

function formatNum(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return Number(n).toLocaleString();
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
