/* Kirdbyys Sports Culling Tool — Frontend */
const API = '/api';
let currentProjectId = null;
let currentProject = null;
let allImages = [];
let currentSort = 'final_score';
let selectedOnly = false;
let pollingInterval = null;

// Theme handling
const html = document.documentElement;
const themeToggle = document.getElementById('theme-toggle');
const brandLogo = document.getElementById('brand-logo');
function applyTheme(theme) {
  html.setAttribute('data-theme', theme);
  brandLogo.src = theme === 'dark' ? '/static/logo-dark.svg' : '/static/logo.svg';
  localStorage.setItem('kirdbyys-theme', theme);
}
const savedTheme = localStorage.getItem('kirdbyys-theme') || 'dark';
applyTheme(savedTheme);
themeToggle.addEventListener('click', () => {
  applyTheme(html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
});

// Navigation
const navItems = document.querySelectorAll('.nav-item');
const views = document.querySelectorAll('.view');
navItems.forEach(item => {
  item.addEventListener('click', () => {
    navItems.forEach(n => n.classList.remove('active'));
    item.classList.add('active');
    const viewId = 'view-' + item.dataset.view;
    views.forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
  if (viewId === 'view-rankings') loadRankings();
  if (viewId === 'view-projects') loadProjects();
  if (viewId === 'view-duplicates') loadDuplicates();
  if (viewId === 'view-selection') loadSelection();
  if (viewId === 'view-export') loadExportSummary();
  if (viewId === 'view-dashboard') loadDashboard();
  });
});

function showToast(message, type='success') {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

async function api(path, options={}) {
  const res = await fetch(API + path, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

async function loadSystemInfo() {
  try {
    const info = await api('/system/info');
    const hw = info.hardware || {};
    const vendor = (hw.gpu_vendor || 'cpu').toUpperCase();
    const rec = info.recommended_providers || [];
    const provider = (rec[0] || 'CPUExecutionProvider').replace('ExecutionProvider', '');
    document.getElementById('system-status').textContent = `${vendor} · ${provider}`;
  } catch (e) {
    document.getElementById('system-status').textContent = 'Offline';
  }
}
loadSystemInfo();

async function loadDashboard() {
  const projects = await api('/projects');
  document.getElementById('stat-projects').textContent = projects.length;
  let total = 0, selected = 0, duplicates = 0;
  for (const p of projects) {
    const stats = await api(`/projects/${p.id}/stats`);
    total += stats.total_images;
    selected += stats.selected;
    duplicates += stats.duplicate_groups;
  }
  document.getElementById('stat-images').textContent = total;
  document.getElementById('stat-selected').textContent = selected;
  document.getElementById('stat-duplicates').textContent = duplicates;
  const list = document.getElementById('project-list');
  if (projects.length === 0) {
    list.innerHTML = `<div class="empty-state"><h3>No projects yet</h3><p>Create a project to start culling.</p></div>`;
  } else {
    list.innerHTML = projects.slice(0, 4).map(p => `
      <div class="project-card" onclick="openProject(${p.id})">
        <h4>${p.name}</h4>
        <p>${p.sport} · ${p.source_folder}</p>
        <span class="badge">${p.status || 'idle'}</span>
      </div>
    `).join('');
  }
  updateProjectSelects(projects);
}

async function loadProjects() {
  const projects = await api('/projects');
  const list = document.getElementById('projects-full-list');
  if (projects.length === 0) {
    list.innerHTML = `<div class="empty-state"><h3>No projects</h3><p>Create a project and import photos.</p></div>`;
  } else {
    list.innerHTML = projects.map(p => `
      <div class="project-card" onclick="openProject(${p.id})">
        <h4>${p.name}</h4>
        <p>${p.sport} · ${p.source_folder}</p>
        <span class="badge">${p.status || 'idle'}</span>
      </div>
    `).join('');
  }
  updateProjectSelects(projects);
}

function updateProjectSelects(projects) {
  const selects = [document.getElementById('target-project')];
  selects.forEach(sel => {
    if (!sel) return;
    sel.innerHTML = projects.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
  });
}

async function openProject(id) {
  currentProjectId = id;
  currentProject = await api(`/projects/${id}`);
  document.getElementById('w-technical').value = (currentProject.weights.technical_quality || 0.25) * 100;
  document.getElementById('w-action').value = (currentProject.weights.action_value || 0.35) * 100;
  document.getElementById('w-story').value = (currentProject.weights.storytelling || 0.25) * 100;
  document.getElementById('w-composition').value = (currentProject.weights.composition || 0.15) * 100;
  updateWeightLabels();
  // Go to rankings if analyzed, else import
  const stats = await api(`/projects/${id}/stats`);
  if (stats.processed > 0) {
    navItems.forEach(n => n.classList.remove('active'));
    document.querySelector('[data-view="rankings"]').classList.add('active');
    views.forEach(v => v.classList.remove('active'));
    document.getElementById('view-rankings').classList.add('active');
    loadRankings();
  } else {
    navItems.forEach(n => n.classList.remove('active'));
    document.querySelector('[data-view="import"]').classList.add('active');
    views.forEach(v => v.classList.remove('active'));
    document.getElementById('view-import').classList.add('active');
  }
}

// New project modal
const projectModal = document.getElementById('project-modal');
function showProjectModal() { projectModal.classList.add('active'); }
function hideProjectModal() { projectModal.classList.remove('active'); }
document.getElementById('btn-create-project').addEventListener('click', showProjectModal);
document.getElementById('btn-new-project').addEventListener('click', showProjectModal);
document.getElementById('project-modal-close').addEventListener('click', hideProjectModal);
document.getElementById('project-modal-backdrop').addEventListener('click', hideProjectModal);
document.getElementById('btn-create-project-confirm').addEventListener('click', async () => {
  const name = document.getElementById('new-project-name').value;
  const sport = document.getElementById('new-project-sport').value;
  const folder = document.getElementById('new-project-folder').value;
  if (!name || !folder) return showToast('Please enter name and folder', 'error');
  const project = await api('/projects', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, sport, source_folder: folder})
  });
  currentProjectId = project.id;
  hideProjectModal();
  showToast(`Project "${name}" created. Importing...`);
  await importFolder(project.id, folder);
  navItems.forEach(n => n.classList.remove('active'));
  document.querySelector('[data-view="rankings"]').classList.add('active');
  views.forEach(v => v.classList.remove('active'));
  document.getElementById('view-rankings').classList.add('active');
  runAnalysis(project.id);
});

// Import
document.getElementById('btn-quick-import').addEventListener('click', () => {
  navItems.forEach(n => n.classList.remove('active'));
  document.querySelector('[data-view="import"]').classList.add('active');
  views.forEach(v => v.classList.remove('active'));
  document.getElementById('view-import').classList.add('active');
});

async function importFolder(projectId, folder) {
  const form = new FormData();
  form.append('folder', folder);
  form.append('copy', 'true');
  const res = await fetch(API + `/projects/${projectId}/import`, {method: 'POST', body: form});
  const data = await res.json();
  showToast(`Imported ${data.imported} images`);
  return data;
}

const dropZone = document.getElementById('drop-zone');
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', async e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  const items = Array.from(e.dataTransfer.items || []);
  const files = Array.from(e.dataTransfer.files || []);
  const projectId = parseInt(document.getElementById('target-project').value);
  if (!projectId) return showToast('Select a project first', 'error');
  const form = new FormData();
  files.forEach(f => form.append('files', f));
  const res = await fetch(API + `/projects/${projectId}/import-files`, {method: 'POST', body: form});
  const data = await res.json();
  showToast(`Imported ${data.imported} images`);
  runAnalysis(projectId);
});

document.getElementById('btn-browse-folder').addEventListener('click', () => document.getElementById('folder-input').click());
document.getElementById('folder-input').addEventListener('change', async e => {
  const files = Array.from(e.target.files);
  const projectId = parseInt(document.getElementById('target-project').value);
  if (!projectId) return showToast('Select a project first', 'error');
  const form = new FormData();
  files.forEach(f => form.append('files', f));
  const res = await fetch(API + `/projects/${projectId}/import-files`, {method: 'POST', body: form});
  const data = await res.json();
  showToast(`Imported ${data.imported} images`);
  runAnalysis(projectId);
});

// Analysis
async function runAnalysis(projectId) {
  const weights = getWeights();
  const topN = parseInt(document.getElementById('top-n-select').value) || 20;
  const res = await fetch(API + `/projects/${projectId}/analyze`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({project_id: projectId, weights, top_n: topN})
  });
  const data = await res.json();
  showToast('Analysis started in background');
  startPolling(data.job_id);
}

function startPolling(jobId) {
  const card = document.getElementById('job-card');
  const fill = document.getElementById('progress-fill');
  const meta = document.getElementById('job-meta');
  const title = card.querySelector('.job-title');
  if (pollingInterval) clearInterval(pollingInterval);
  pollingInterval = setInterval(async () => {
    const job = await api(`/jobs/${jobId}`);
    title.textContent = `Job: ${job.job_type}`;
    fill.style.width = (job.progress * 100) + '%';
    meta.textContent = `${job.status} · ${job.processed_items}/${job.total_items} · ${job.message || ''}`;
    if (job.status === 'complete' || job.status === 'error' || job.status === 'cancelled') {
      clearInterval(pollingInterval);
      fill.style.width = '100%';
      showToast(job.status === 'complete' ? 'Analysis complete!' : `Job ${job.status}`);
      loadRankings();
      loadDashboard();
    }
  }, 1000);
}

function getWeights() {
  return {
    technical_quality: parseInt(document.getElementById('w-technical').value) / 100,
    action_value: parseInt(document.getElementById('w-action').value) / 100,
    storytelling: parseInt(document.getElementById('w-story').value) / 100,
    composition: parseInt(document.getElementById('w-composition').value) / 100
  };
}

function updateWeightLabels() {
  document.getElementById('w-technical-val').textContent = document.getElementById('w-technical').value + '%';
  document.getElementById('w-action-val').textContent = document.getElementById('w-action').value + '%';
  document.getElementById('w-story-val').textContent = document.getElementById('w-story').value + '%';
  document.getElementById('w-composition-val').textContent = document.getElementById('w-composition').value + '%';
}
['w-technical','w-action','w-story','w-composition'].forEach(id => {
  document.getElementById(id).addEventListener('input', updateWeightLabels);
});

document.getElementById('btn-reanalyze').addEventListener('click', async () => {
  if (!currentProjectId) return showToast('Open a project first', 'error');
  await api(`/projects/${currentProjectId}/weights`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({weights: getWeights()})
  });
  runAnalysis(currentProjectId);
});

// Rankings
async function loadRankings() {
  if (!currentProjectId) return;
  const limit = document.getElementById('top-n-select').value === 'all' ? 2000 : parseInt(document.getElementById('top-n-select').value);
  const params = new URLSearchParams({sort_by: currentSort, order: 'desc', limit: String(limit)});
  if (selectedOnly) params.set('selected_only', 'true');
  allImages = await api(`/projects/${currentProjectId}/images?${params}`);
  renderGallery(allImages);
}

function renderGallery(images) {
  const gallery = document.getElementById('rankings-gallery');
  if (!images.length) {
    gallery.innerHTML = `<div class="empty-state"><h3>No images yet</h3><p>Import and analyze a project first.</p></div>`;
    return;
  }
  gallery.innerHTML = images.map(img => {
    const moments = (img.moments || []).slice(0, 2).map(m => `<span class="tag tag-primary">${m.replace(/_/g, ' ')}</span>`).join('');
    return `
      <div class="photo-card ${img.selected ? 'selected' : ''} ${img.duplicate_group_id ? 'duplicate' : ''}" data-id="${img.id}" onclick="openImage(${img.id})">
        <div class="thumb"><img src="/api/images/${img.id}/thumbnail" loading="lazy" alt=""></div>
        <div class="overlay">
          <span class="rank-badge">#${img.rank || '-'}</span>
          <span class="score-badge">${(img.final_score || 0).toFixed(1)}</span>
        </div>
        <div class="info">
          <div class="filename">${img.filename}</div>
          <div class="meta">T ${(img.technical_score || 0).toFixed(0)} · A ${(img.action_score || 0).toFixed(0)} · S ${(img.storytelling_score || 0).toFixed(0)} · C ${(img.composition_score || 0).toFixed(0)}</div>
          <div class="tags">${moments}</div>
        </div>
      </div>
    `;
  }).join('');
}

document.getElementById('sort-select').addEventListener('change', e => { currentSort = e.target.value; loadRankings(); });
document.getElementById('top-n-select').addEventListener('change', loadRankings);
document.getElementById('btn-filter-selected').addEventListener('click', () => {
  selectedOnly = !selectedOnly;
  document.getElementById('btn-filter-selected').classList.toggle('btn-ghost');
  document.getElementById('btn-filter-selected').classList.toggle('btn-primary');
  loadRankings();
});

// Image detail modal
const detailModal = document.getElementById('detail-modal');
let currentDetailImage = null;
window.openImage = async function(id) {
  currentDetailImage = await api(`/images/${id}`);
  const img = currentDetailImage;
  document.getElementById('modal-img').src = `/api/images/${id}/preview`;
  document.getElementById('modal-filename').textContent = img.filename;
  document.getElementById('modal-explanation').textContent = img.explanation || 'No explanation available.';
  document.getElementById('modal-moments').innerHTML = (img.moments || []).map(m => `<span class="tag tag-primary">${m.replace(/_/g, ' ')}</span>`).join('');
  renderScoreRings(img);
  renderBreakdown('modal-tech-breakdown', img.quality_breakdown);
  renderBreakdown('modal-action-breakdown', img.action_breakdown);
  renderBreakdown('modal-comp-breakdown', img.composition_breakdown);
  detailModal.classList.add('active');
};
function renderScoreRings(img) {
  const scores = [
    {label: 'Overall', value: img.final_score || 0},
    {label: 'Technical', value: img.technical_score || 0},
    {label: 'Action', value: img.action_score || 0},
    {label: 'Story', value: img.storytelling_score || 0},
    {label: 'Comp', value: img.composition_score || 0}
  ];
  document.getElementById('modal-scores').innerHTML = scores.map(s => {
    const pct = Math.min(100, Math.max(0, s.value));
    const dash = 2 * Math.PI * 26;
    const offset = dash - (pct / 100) * dash;
    return `
      <div class="score-ring">
        <svg viewBox="0 0 64 64">
          <circle class="bg" cx="32" cy="32" r="26"/>
          <circle class="fg" cx="32" cy="32" r="26" stroke-dasharray="${dash}" stroke-dashoffset="${offset}"/>
        </svg>
        <div class="value">${pct.toFixed(1)}</div>
        <div class="label">${s.label}</div>
      </div>
    `;
  }).join('');
}
function renderBreakdown(containerId, data) {
  const container = document.getElementById(containerId);
  if (!data || Object.keys(data).length === 0) {
    container.innerHTML = '<div class="empty-state">No data</div>'; return;
  }
  container.innerHTML = Object.entries(data).map(([k, v]) => {
    const pct = Math.min(100, Math.max(0, typeof v === 'number' ? v : 0));
    return `
      <div class="breakdown-item">
        <span>${k.replace(/_/g, ' ')}</span>
        <div class="bar"><div class="bar-fill" style="width:${pct}%"></div></div>
        <span>${pct.toFixed(0)}</span>
      </div>
    `;
  }).join('');
}
function hideDetailModal() { detailModal.classList.remove('active'); }
document.getElementById('modal-close').addEventListener('click', hideDetailModal);
document.getElementById('modal-backdrop').addEventListener('click', hideDetailModal);
document.getElementById('modal-select').addEventListener('click', async () => {
  if (!currentDetailImage) return;
  await api(`/images/${currentDetailImage.id}/select`, {method: 'POST', body: new URLSearchParams({selected: 'true'})});
  showToast('Image selected');
  loadRankings();
});
document.getElementById('modal-reject').addEventListener('click', async () => {
  if (!currentDetailImage) return;
  await api(`/images/${currentDetailImage.id}/select`, {method: 'POST', body: new URLSearchParams({selected: 'false'})});
  showToast('Image rejected');
  loadRankings();
});

// Duplicates
async function loadDuplicates() {
  if (!currentProjectId) return;
  const groups = await api(`/projects/${currentProjectId}/duplicates`);
  const list = document.getElementById('duplicates-list');
  if (!groups.length) {
    list.innerHTML = `<div class="empty-state"><h3>No duplicates found</h3><p>Burst sequences and near-duplicates will appear here.</p></div>`; return;
  }
  list.innerHTML = '';
  for (const g of groups) {
    const imgs = await api(`/projects/${currentProjectId}/images?limit=2000`);
    const groupImages = imgs.filter(i => g.image_ids && g.image_ids.includes(i.id) || i.duplicate_group_id === g.id);
    list.innerHTML += `
      <div class="dup-group">
        <h4>Burst / Duplicate Group — ${groupImages.length} frames · Best: #${g.representative_image_id}</h4>
        <div class="gallery">${groupImages.slice(0, 8).map(img => `
          <div class="photo-card ${img.id === g.representative_image_id ? 'selected' : ''}" onclick="openImage(${img.id})">
            <div class="thumb"><img src="/api/images/${img.id}/thumbnail" loading="lazy"></div>
            <div class="overlay"><span class="score-badge">${(img.final_score || 0).toFixed(1)}</span></div>
          </div>
        `).join('')}</div>
      </div>
    `;
  }
}

// Final Selection
async function loadSelection() {
  if (!currentProjectId) return;
  const sortBy = document.getElementById('selection-sort').value;
  const params = new URLSearchParams({selected_only: 'true', sort_by: sortBy, order: 'asc', limit: '2000'});
  const images = await api(`/projects/${currentProjectId}/images?${params}`);
  const gallery = document.getElementById('selection-gallery');
  if (!images.length) {
    gallery.innerHTML = `<div class="empty-state"><h3>No images selected yet</h3><p>Run analysis and review the rankings to make selections.</p></div>`;
    return;
  }
  gallery.innerHTML = images.map(img => {
    const moments = (img.moments || []).slice(0, 2).map(m => `<span class="tag tag-primary">${m.replace(/_/g, ' ')}</span>`).join('');
    return `
      <div class="photo-card selected" data-id="${img.id}" onclick="openImage(${img.id})">
        <div class="thumb"><img src="/api/images/${img.id}/thumbnail" loading="lazy" alt=""></div>
        <div class="overlay">
          <span class="rank-badge">#${img.rank || '-'}</span>
          <span class="score-badge">${(img.final_score || 0).toFixed(1)}</span>
        </div>
        <div class="info">
          <div class="filename">${img.filename}</div>
          <div class="meta">T ${(img.technical_score || 0).toFixed(0)} · A ${(img.action_score || 0).toFixed(0)} · S ${(img.storytelling_score || 0).toFixed(0)} · C ${(img.composition_score || 0).toFixed(0)}</div>
          <div class="tags">${moments}</div>
        </div>
      </div>
    `;
  }).join('');
}

document.getElementById('selection-sort').addEventListener('change', loadSelection);
document.getElementById('btn-export-selection').addEventListener('click', () => {
  navItems.forEach(n => n.classList.remove('active'));
  document.querySelector('[data-view="export"]').classList.add('active');
  views.forEach(v => v.classList.remove('active'));
  document.getElementById('view-export').classList.add('active');
});

async function loadExportSummary() {
  // Optional: show count of selected images in export view
}

// Export
const exportMode = document.getElementById('export-mode');
const exportDestGroup = document.getElementById('export-destination-group');
exportMode.addEventListener('change', () => {
  exportDestGroup.style.display = ['copy', 'move'].includes(exportMode.value) ? 'block' : 'none';
});
document.getElementById('btn-export').addEventListener('click', async () => {
  if (!currentProjectId) return showToast('Open a project first', 'error');
  const mode = exportMode.value;
  const topN = parseInt(document.getElementById('export-top-n').value);
  const destination = document.getElementById('export-destination').value || null;
  const res = await fetch(API + `/projects/${currentProjectId}/export`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mode, top_n: topN, destination})
  });
  const data = await res.json();
  document.getElementById('export-result').innerHTML = `<div class="stat-card"><p>Exported ${data.count} files to</p><a href="file://${data.path}" target="_blank">${data.path}</a></div>`;
  showToast('Export complete');
});

// Init
loadDashboard();
