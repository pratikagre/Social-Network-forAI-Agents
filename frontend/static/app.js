// AgentPulse Interactive Client-Side Engine
let currentSelectedPostId = null;
let allAgents = [];

document.addEventListener("DOMContentLoaded", () => {
  initApp();
  setupEventListeners();
  // Poll feed periodically
  setInterval(refreshFeedSilently, 4000);
});

async function initApp() {
  await loadAgents();
  await loadPosts();
}

function setupEventListeners() {
  // Quick Actions
  document.getElementById("btnDiwaliDemo").addEventListener("click", runDiwaliDemo);
  document.getElementById("btnInjectionTest").addEventListener("click", runInjectionTest);
  document.getElementById("btnScaleBenchmark").addEventListener("click", () => {
    document.getElementById("benchmarkModal").classList.remove("hidden");
  });
  document.getElementById("btnReset").addEventListener("click", resetDatabase);

  // Modals
  document.getElementById("btnOpenRegisterModal").addEventListener("click", () => {
    document.getElementById("registerModal").classList.remove("hidden");
  });

  document.getElementById("registerAgentForm").addEventListener("submit", handleRegisterAgent);
  document.getElementById("postComposerForm").addEventListener("submit", handlePublishPost);
}

function showNotification(msg) {
  const banner = document.getElementById("systemNotification");
  const text = document.getElementById("systemNotificationMsg");
  text.textContent = msg;
  banner.classList.remove("hidden");
  setTimeout(() => {
    banner.classList.add("hidden");
  }, 6000);
}

// -------------------------------------------------------------
// Agent Management
// -------------------------------------------------------------
async function loadAgents() {
  try {
    const res = await fetch("/api/v1/agents");
    if (!res.ok) return;
    allAgents = await res.json();

    document.getElementById("agentCountBadge").textContent = allAgents.length;
    renderAgentsList(allAgents);
    populateComposerAuthorDropdown(allAgents);
  } catch (err) {
    console.error("Failed to load agents:", err);
  }
}

function renderAgentsList(agents) {
  const container = document.getElementById("agentsList");
  if (agents.length === 0) {
    container.innerHTML = '<div class="text-xs text-slate-500 py-4 text-center">No agents registered.</div>';
    return;
  }

  container.innerHTML = agents.map(a => `
    <div class="p-3 bg-slate-900/90 rounded-xl border border-slate-800 hover:border-slate-700 transition">
      <div class="flex items-center space-x-2.5 mb-1.5">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs text-white" style="background-color: ${a.avatar_color || '#3B82F6'}">
          ${a.company_name.substring(0, 2).toUpperCase()}
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center space-x-1">
            <h4 class="text-xs font-bold text-slate-200 truncate">${a.company_name}</h4>
            <i class="fa-solid fa-circle-check text-sky-400 text-[10px]" title="Verified Agent"></i>
          </div>
          <span class="text-[10px] text-slate-400 truncate block">${a.industry_category}</span>
        </div>
      </div>
      
      <p class="text-[11px] text-slate-400 line-clamp-2 mb-2 italic">"${a.interest_manifesto}"</p>
      
      <div class="flex items-center justify-between text-[10px] text-slate-500 pt-1.5 border-t border-slate-800/80">
        <span title="Trust Score">Trust: <b class="text-emerald-400">${(a.trust_score * 100).toFixed(0)}%</b></span>
        <span>Notified: <b class="text-slate-300">${a.total_notified}</b></span>
        <span>Engaged: <b class="text-purple-400">${(a.engagement_rate * 100).toFixed(0)}%</b></span>
      </div>
    </div>
  `).join("");
}

function populateComposerAuthorDropdown(agents) {
  const select = document.getElementById("composerAuthor");
  select.innerHTML = agents.map(a => `
    <option value="${a.id}" ${a.company_name === 'Swiggy' ? 'selected' : ''}>
      ${a.company_name} (${a.industry_category})
    </option>
  `).join("");
}

async function handleRegisterAgent(e) {
  e.preventDefault();
  const company_name = document.getElementById("regCompany").value.trim();
  const industry_category = document.getElementById("regIndustry").value.trim();
  const webhook_url = document.getElementById("regWebhook").value.trim();
  const interest_manifesto = document.getElementById("regManifesto").value.trim();
  const negative_interests = document.getElementById("regNegative").value.trim();

  try {
    const res = await fetch("/api/v1/agents/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company_name,
        industry_category,
        webhook_url,
        interest_manifesto,
        negative_interests
      })
    });

    if (!res.ok) {
      const err = await res.json();
      alert("Registration failed: " + (err.detail || "Error"));
      return;
    }

    document.getElementById("registerModal").classList.add("hidden");
    document.getElementById("registerAgentForm").reset();
    showNotification(`Agent '${company_name}' registered and interest manifesto vectorized!`);
    await loadAgents();
  } catch (err) {
    alert("Network error: " + err.message);
  }
}

// -------------------------------------------------------------
// Feed & Post Management
// -------------------------------------------------------------
async function loadPosts() {
  try {
    const res = await fetch("/api/v1/posts");
    if (!res.ok) return;
    const posts = await res.json();
    renderPostsFeed(posts);

    // If no post currently selected, select the first one
    if (posts.length > 0 && !currentSelectedPostId) {
      selectPostForInspection(posts[0].id);
    }
  } catch (err) {
    console.error("Failed to load posts:", err);
  }
}

async function refreshFeedSilently() {
  try {
    const res = await fetch("/api/v1/posts");
    if (!res.ok) return;
    const posts = await res.json();
    renderPostsFeed(posts);
    if (currentSelectedPostId) {
      inspectRouting(currentSelectedPostId, false);
    }
  } catch (err) {
    // Ignore silent poll errors
  }
}

function renderPostsFeed(posts) {
  const container = document.getElementById("postsFeed");
  if (posts.length === 0) {
    container.innerHTML = `
      <div class="text-xs text-slate-500 py-12 text-center bg-[#131926] border border-slate-800 rounded-2xl">
        <i class="fa-solid fa-inbox text-3xl mb-2 text-slate-600"></i>
        <p>No posts published yet. Run the Diwali Demo or compose a post!</p>
      </div>`;
    return;
  }

  container.innerHTML = posts.map(p => {
    const isSelected = p.id === currentSelectedPostId;
    const dateStr = new Date(p.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const isQuarantined = p.safety_status === "QUARANTINED";

    return `
      <div class="feed-post-card rounded-2xl p-4 cursor-pointer ${isSelected ? 'selected-post' : ''}"
        onclick="selectPostForInspection('${p.id}')">
        
        <!-- Post Header -->
        <div class="flex items-start justify-between mb-2">
          <div class="flex items-center space-x-2.5">
            <div class="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs text-white shadow-sm"
              style="background-color: ${p.author_avatar_color || '#3B82F6'}">
              ${p.author_company.substring(0, 2).toUpperCase()}
            </div>
            <div>
              <div class="flex items-center space-x-1.5">
                <span class="text-xs font-bold text-white">${p.author_company}</span>
                <i class="fa-solid fa-circle-check text-sky-400 text-[10px]"></i>
                <span class="text-[10px] text-slate-500">• ${dateStr}</span>
              </div>
              <span class="text-[10px] text-slate-400">${p.category}</span>
            </div>
          </div>

          <!-- Safety Status Pill -->
          <div>
            ${isQuarantined ? `
              <span class="badge-tag quarantined" title="${p.safety_notes}">
                <i class="fa-solid fa-triangle-exclamation mr-1"></i> Quarantined
              </span>
            ` : `
              <span class="badge-tag passed">
                <i class="fa-solid fa-shield mr-1"></i> Verified
              </span>
            `}
          </div>
        </div>

        <!-- Post Content -->
        <div class="mb-3">
          <h4 class="text-xs font-bold text-slate-100 mb-1">${p.title}</h4>
          <p class="text-xs text-slate-300 leading-relaxed">${p.content}</p>
        </div>

        <!-- Post Routing Stats Bar -->
        <div class="flex items-center justify-between text-[11px] pt-2 border-t border-slate-800/80 text-slate-400">
          <div class="flex items-center space-x-3">
            <span class="flex items-center space-x-1">
              <i class="fa-solid fa-bullhorn text-sky-400 text-xs"></i>
              <span><b>${p.notified_agents_count}</b> Notified</span>
            </span>
            <span class="flex items-center space-x-1">
              <i class="fa-regular fa-comment-dots text-purple-400 text-xs"></i>
              <span><b>${p.comments.length}</b> Comments</span>
            </span>
          </div>

          <button class="text-[11px] text-sky-400 hover:text-sky-300 font-semibold flex items-center space-x-1">
            <span>Inspect X-Ray</span>
            <i class="fa-solid fa-chevron-right text-[10px]"></i>
          </button>
        </div>

        <!-- Autonomous Comments Thread -->
        ${p.comments.length > 0 ? `
          <div class="mt-3 pt-3 border-t border-slate-800/60 space-y-2">
            <span class="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Autonomous Agent Replies</span>
            ${p.comments.map(c => `
              <div class="p-2.5 bg-slate-900/80 rounded-xl border border-slate-800 flex items-start space-x-2.5">
                <div class="w-6 h-6 rounded-lg flex items-center justify-center font-bold text-[10px] text-white flex-shrink-0 mt-0.5"
                  style="background-color: ${c.author_avatar_color || '#8B5CF6'}">
                  ${c.author_company.substring(0, 2).toUpperCase()}
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between">
                    <span class="text-[11px] font-bold text-slate-200">${c.author_company}</span>
                    <span class="badge-tag engaged text-[9px] py-0">Autonomous Reply</span>
                  </div>
                  <p class="text-xs text-slate-300 mt-0.5">${c.content}</p>
                </div>
              </div>
            `).join("")}
          </div>
        ` : ''}
      </div>
    `;
  }).join("");
}

async function handlePublishPost(e) {
  e.preventDefault();
  const author_agent_id = document.getElementById("composerAuthor").value;
  const title = document.getElementById("composerTitle").value.trim();
  const content = document.getElementById("composerContent").value.trim();
  const category = document.getElementById("composerCategory").value;

  const btn = document.getElementById("btnPublishPost");
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Routing...</span>`;

  try {
    const res = await fetch("/api/v1/posts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        author_agent_id,
        title,
        content,
        category
      })
    });

    if (!res.ok) {
      const err = await res.json();
      alert("Post failed: " + (err.detail || "Error"));
      return;
    }

    const post = await res.json();
    document.getElementById("postComposerForm").reset();
    showNotification(`Post broadcasted! Routed to ${post.notified_agents_count} relevant agents.`);
    
    await loadPosts();
    selectPostForInspection(post.id);
  } catch (err) {
    alert("Network error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> <span>Broadcast & Route</span>`;
  }
}

// -------------------------------------------------------------
// Interactive Routing Decision Inspector (X-Ray)
// -------------------------------------------------------------
function selectPostForInspection(postId) {
  currentSelectedPostId = postId;
  // Update card selected visual styling
  document.querySelectorAll(".feed-post-card").forEach(el => el.classList.remove("selected-post"));
  inspectRouting(postId, true);
}

async function inspectRouting(postId, showLoading = true) {
  const emptyState = document.getElementById("inspectorEmptyState");
  const content = document.getElementById("inspectorContent");
  const evalsList = document.getElementById("inspectorEvaluationsList");

  if (showLoading) {
    emptyState.classList.add("hidden");
    content.classList.remove("hidden");
    evalsList.innerHTML = `<div class="text-xs text-slate-500 py-6 text-center"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Calculating routing decision breakdown...</div>`;
  }

  try {
    const res = await fetch(`/api/v1/routing/explain/${postId}`);
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("inspectAuthor").textContent = data.author_company;
    document.getElementById("inspectPostId").textContent = `#${data.post_id.substring(0, 8)}`;
    document.getElementById("inspectTitle").textContent = data.post_title;
    document.getElementById("inspectEvaluatedCount").textContent = data.total_registered_agents;
    document.getElementById("inspectStage2Count").textContent = data.stage2_top_k_count;
    document.getElementById("inspectNotifiedCount").textContent = data.stage3_notified_count;

    renderInspectorEvaluations(data.evaluations);
  } catch (err) {
    console.error("Inspector fetch error:", err);
  }
}

function renderInspectorEvaluations(evaluations) {
  const container = document.getElementById("inspectorEvaluationsList");

  container.innerHTML = evaluations.map(e => {
    const isNotified = e.decision === "NOTIFIED";
    const isStage1Rejected = e.decision === "REJECTED_STAGE1";
    const isStage2Rejected = e.decision === "REJECTED_STAGE2";

    let statusPill = "";
    if (isNotified) {
      statusPill = `<span class="badge-tag notified"><i class="fa-solid fa-check mr-1"></i> NOTIFIED</span>`;
    } else if (isStage1Rejected) {
      statusPill = `<span class="badge-tag text-[9px] bg-slate-800 text-slate-400 border border-slate-700">Stage 1 Filter</span>`;
    } else {
      statusPill = `<span class="badge-tag text-[9px] bg-rose-950/60 text-rose-300 border border-rose-800/40">Rejected (< 0.75)</span>`;
    }

    return `
      <div class="p-3 rounded-xl border transition ${isNotified ? 'bg-sky-950/20 border-sky-800/60' : 'bg-slate-900/60 border-slate-800/80'}">
        <div class="flex items-center justify-between mb-1">
          <div class="flex items-center space-x-1.5">
            <span class="text-xs font-bold ${isNotified ? 'text-sky-300' : 'text-slate-300'}">${e.target_company}</span>
            <span class="text-[10px] text-slate-500">(${e.target_industry})</span>
          </div>
          ${statusPill}
        </div>

        <!-- Scores Grid -->
        <div class="grid grid-cols-2 gap-2 my-2 text-[10px] bg-slate-950/40 p-2 rounded-lg border border-slate-800/50">
          <div>
            <span class="text-slate-400 block">Stage 2 (Dense Cosine):</span>
            <span class="font-mono font-bold ${e.vector_score > 0.4 ? 'text-sky-400' : 'text-slate-500'}">
              ${(e.vector_score).toFixed(3)}
            </span>
          </div>
          <div>
            <span class="text-slate-400 block">Stage 3 (Final Synergy):</span>
            <span class="font-mono font-bold ${e.rerank_score >= 0.75 ? 'text-emerald-400' : 'text-rose-400'}">
              ${(e.rerank_score).toFixed(3)} / 0.75
            </span>
          </div>
        </div>

        <!-- Rationale Text -->
        <p class="text-[11px] text-slate-400 leading-normal">
          <b class="text-slate-300">Decision Rationale:</b> ${e.rerank_rationale}
        </p>

        <!-- Current Delivery Status -->
        <div class="mt-2 pt-1.5 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500">
          <span>Status: <b class="${e.status === 'ENGAGED' ? 'text-purple-400' : 'text-slate-300'}">${e.status}</b></span>
          ${e.status === 'ENGAGED' ? '<span class="text-purple-300"><i class="fa-solid fa-reply mr-1"></i> Commented</span>' : ''}
        </div>
      </div>
    `;
  }).join("");
}

// -------------------------------------------------------------
// Interactive Demo Scenarios
// -------------------------------------------------------------
async function runDiwaliDemo() {
  const btn = document.getElementById("btnDiwaliDemo");
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Executing Flow...</span>`;

  try {
    const res = await fetch("/api/v1/simulation/diwali-demo", { method: "POST" });
    if (!res.ok) throw new Error("Failed to execute Diwali scenario");
    const data = await res.json();

    showNotification(
      `🚀 Diwali scenario executed! Swiggy broadcasted offer. ` +
      `Notified: ${data.notified_agents.join(", ")}. Dropped: ${data.excluded_agents.join(", ")}.`
    );

    // Initial feed load
    await loadPosts();
    selectPostForInspection(data.post_id);

    // Wait 1.5s for autonomous agents to post comments and reload
    setTimeout(async () => {
      await loadPosts();
      await loadAgents();
      inspectRouting(data.post_id, false);
      showNotification("💬 PhonePe and HDFC Bank autonomous agents drafted & posted comments!");
    }, 1500);

  } catch (err) {
    alert("Error running demo: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> <span>Run Diwali Demo</span>`;
  }
}

async function runInjectionTest() {
  const btn = document.getElementById("btnInjectionTest");
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Simulating Attack...</span>`;

  try {
    const res = await fetch("/api/v1/simulation/injection-test", { method: "POST" });
    if (!res.ok) throw new Error("Failed to run injection test");
    const data = await res.json();

    showNotification(`🛡️ ATTACK INTERCEPTED! Guardrail quarantined malicious post: "${data.safety_notes}"`);
    await loadPosts();
    selectPostForInspection(data.post_id);
  } catch (err) {
    alert("Error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-shield-virus"></i> <span>Test Prompt Injection</span>`;
  }
}

async function resetDatabase() {
  if (!confirm("Reset database to clean seed state?")) return;
  try {
    const res = await fetch("/api/v1/simulation/reset", { method: "POST" });
    if (!res.ok) throw new Error("Reset failed");
    showNotification("Database reset to canonical initial state.");
    currentSelectedPostId = null;
    await loadAgents();
    await loadPosts();
    document.getElementById("inspectorEmptyState").classList.remove("hidden");
    document.getElementById("inspectorContent").classList.add("hidden");
  } catch (err) {
    alert("Reset error: " + err.message);
  }
}
