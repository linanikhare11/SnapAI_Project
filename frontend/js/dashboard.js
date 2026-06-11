/* SnapAI — Dashboard JS */

// ── Mobile Sidebar Toggle ─────────────────────────────────────────────────────
function setupSidebarToggle() {
  const toggle = document.getElementById('sidebar-toggle');
  const overlay = document.getElementById('sidebar-overlay');
  const sidebar = document.getElementById('sidebar');
  
  if (!toggle) return;
  
  function closeSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
  }
  
  function toggleSidebar() {
    const isOpen = sidebar.classList.contains('open');
    if (isOpen) {
      closeSidebar();
    } else {
      sidebar.classList.add('open');
      overlay.classList.add('active');
    }
  }
  
  toggle.addEventListener('click', toggleSidebar);
  overlay.addEventListener('click', closeSidebar);
  
  // Close on nav link click
  document.querySelectorAll('.sidebar-nav a').forEach(link => {
    link.addEventListener('click', closeSidebar);
  });
  
  // Close on window resize if screen is large enough
  window.addEventListener('resize', () => {
    if (window.innerWidth > 1024) {
      closeSidebar();
    }
  });
}

// ── Auth Guard ────────────────────────────────────────────────────────────────
if (!Api.getToken()) {
  window.location.href = '/login';
}

// ── State ─────────────────────────────────────────────────────────────────────
let photographer = Api.getPhotographer() || {};
let allEvents    = [];
let selectedEventId = null;
let uploadFiles_ = [];
let indexingTimer = null;
let previousSectionBeforeDetail = 'events';
let previousSectionBeforeShare = 'events';
let pendingDeleteEventId = null;
let profileLoaded = false;
const THEME_STORAGE_KEY = 'snapai_theme';
let profileChatMessages = [];

function applyTheme(themeName) {
  const theme = themeName === 'light' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', theme);
}

function getSavedTheme() {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    return saved === 'light' ? 'light' : 'dark';
  } catch {
    return 'dark';
  }
}

function saveTheme(themeName) {
  const theme = themeName === 'light' ? 'light' : 'dark';
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Ignore storage errors (private mode / blocked storage)
  }
  applyTheme(theme);
}

// ── Pagination State ──────────────────────────────────────────────────────────
let allLoadedPhotos = [];
let photosDisplayedCount = 0;
let isPhotosExpanded = false;
const PHOTOS_PER_PAGE = 8;

// ── Init ──────────────────────────────────────────────────────────────────────
(async () => {
  applyTheme(getSavedTheme());
  setupSidebarToggle();
  await loadPhotographerProfile();
  setupSidebarUser();
  
  await loadOverview();
  
  await loadEvents();

  const initialDetailEventId = getInitialDetailEventId();
  if (initialDetailEventId) {
    await openEventDetail(initialDetailEventId);
  }
  
  // Clear query parameters from URL so refresh shows dashboard instead of event detail
  window.history.replaceState({}, document.title, window.location.pathname);
  
  populateEventSelect();
  loadSettings();
  setupDragDrop();
  setupPublicToggle();
})();

async function loadPhotographerProfile() {
  try {
    const profile = await Api.getProfile();
    photographer = profile || photographer;
    Api.savePhotographer(photographer);
    profileLoaded = true;
  } catch (err) {
    profileLoaded = false;
  }
}

function getInitialDetailEventId() {
  const params = new URLSearchParams(window.location.search);
  const view = params.get('view');
  const eventId = params.get('eventId');
  if (view !== 'detail' || !eventId) return null;

  const parsed = Number.parseInt(eventId, 10);
  if (!Number.isFinite(parsed)) return null;
  return parsed;
}

function setupSidebarUser() {
  const name = photographer.name || '?';
  document.getElementById('sidebar-name').textContent = name;
  const parts = name.split(' ').filter(Boolean);
  const initials = parts.length > 1
    ? `${parts[0][0] || ''}${parts[1][0] || ''}`.toUpperCase()
    : name.charAt(0).toUpperCase();
  document.getElementById('sidebar-avatar').textContent = initials || '?';
  const today = new Date().getHours();
  const greet = today < 12 ? 'Good morning' : today < 17 ? 'Good afternoon' : 'Good evening';
  const h1 = document.querySelector('#section-overview .dash-header h1');
  if (h1) h1.textContent = `${greet} ${name.split(' ')[0]} 👋`;
}

// ── Section Switcher ──────────────────────────────────────────────────────────
function switchSection(tab, linkEl) {
  document.querySelectorAll('.dash-section').forEach(s => s.style.display = 'none');
  document.querySelectorAll('.sidebar-nav a').forEach(a => a.classList.remove('active'));
  document.getElementById(`section-${tab}`).style.display = '';
  if (linkEl) linkEl.classList.add('active');
  else {
    const el = document.querySelector(`[data-tab="${tab}"]`);
    if (el) el.classList.add('active');
  }

  if (tab === 'profile') {
    loadContactInfo();
    loadPhotographyInfo();
  }

  return false;
}

// ── OVERVIEW ─────────────────────────────────────────────────────────────────
async function loadOverview() {
  try {
    const data = await Api.dashSummary();
    
    document.getElementById('stat-events').textContent = data.total_events;
    document.getElementById('stat-photos').textContent = data.total_photos.toLocaleString();

    // Count indexed
    const indexed = (data.recent_events || []).filter(e => e.is_indexed).length;
    document.getElementById('stat-indexed').textContent = indexed;
    document.getElementById('stat-storage').textContent = data.total_photos.toLocaleString() + ' files';

    renderEventCards(data.recent_events || [], 'recent-events-grid', true);
    document.getElementById('overview-empty').style.display = data.total_events === 0 ? '' : 'none';
  } catch (err) {
  }
}

// ── EVENTS ───────────────────────────────────────────────────────────────────
async function loadEvents() {
  try {
    const data = await Api.listEvents();
    
    allEvents = data || [];
    
    // Clear search input when loading events
    const searchInput = document.getElementById('event-search-input');
    if (searchInput) searchInput.value = '';
    
    renderEventCards(allEvents, 'all-events-grid', false);
    document.getElementById('events-empty').style.display = allEvents.length === 0 ? '' : 'none';
    populateEventSelect();
  } catch (err) {
  }
}

function renderEventCards(events, containerId, isOverview) {
  const grid = document.getElementById(containerId);
  if (!grid) {
    return;
  }

  // Clear non-empty-state children
  Array.from(grid.children).forEach(c => {
    if (!c.classList.contains('empty-state')) c.remove();
  });

  events.forEach(ev => {
    const card = document.createElement('div');
    card.className = 'event-card fade-up';
    const dateStr = ev.event_date
      ? new Date(ev.event_date).toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' })
      : 'No date set';

    const galleryUrl = `/gallery/${ev.slug}`;
    
    // Display cover image if available, otherwise show theme image
    let coverHtml = `<div class="event-card-cover">📷</div>`;
    // Add event ID as cache-buster so different events get different random theme images
    const themeUrl = `/api/themes/${ev.event_type || 'general'}?eventId=${ev.id}`;
    const fallbackThemeUrl = `/api/themes/general?eventId=${ev.id}`;
    
    if (ev.cover_image) {
      // Show user's custom cover photo
      coverHtml = `<div class="event-card-cover">
        <img src="/api/photos/thumbnail/${ev.id}/${ev.cover_image}" alt="Event cover" style="width:100%;height:100%;object-fit:cover;" />
      </div>`;
    } else {
      // Show theme image as fallback
      coverHtml = `<div class="event-card-cover">
        <img src="${themeUrl}" alt="Event theme" style="width:100%;height:100%;object-fit:cover;" onerror="if(!this.dataset.fallback){this.dataset.fallback='1'; this.src='${fallbackThemeUrl}';} else {this.style.backgroundColor='rgba(0,0,0,0.3)';}" />
      </div>`;
    }

    card.innerHTML = `
      ${coverHtml}
      <div class="event-card-body">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
          <div class="event-card-title">${escHtml(ev.title)}</div>
          <button onclick="openEditEventModal(${ev.id})" style="background:none; border:none; font-size:1rem; cursor:pointer; padding:0.25rem; color:var(--gold); hover:opacity:0.8; transition:opacity 0.2s;" title="Edit event">✏️</button>
        </div>
        <div class="event-card-meta">
          <span>📅 ${dateStr}</span>
          <span>${ev.is_public ? '🔓 Public' : '🔒 Private'}</span>
        </div>
        <div class="event-card-actions">
          <button class="btn btn-sm btn-gold" onclick="openEventDetail(${ev.id})">Manage</button>
          <button class="btn btn-sm btn-share-icon share-btn event-icon-btn" data-gallery-url="${galleryUrl}" data-event-title="${escHtml(ev.title)}" title="Share event">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
          <button class="btn btn-sm btn-danger event-icon-btn" onclick="deleteEvent(${ev.id}, '${escHtml(ev.title)}', event)" title="Delete event">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
              <path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
            </svg>
          </button>
        </div>
      </div>`;
    grid.appendChild(card);
  });
  
  // Attach event listeners to share buttons
  document.querySelectorAll('.share-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      const galleryUrl = this.getAttribute('data-gallery-url');
      const eventTitle = this.getAttribute('data-event-title');
      if (galleryUrl && eventTitle) {
        openShareModal(galleryUrl, eventTitle);
      } else {
        toast('Error: Missing event information', 'error');
      }
    });
  });
}

// ── Event Search & Filter ────────────────────────────────────────────────────
function filterEvents() {
  const searchInput = document.getElementById('event-search-input');
  const searchTerm = searchInput.value.toLowerCase().trim();
  
  // Filter events based on search term
  const filteredEvents = searchTerm === '' 
    ? allEvents 
    : allEvents.filter(event => event.title.toLowerCase().includes(searchTerm));
  
  // Re-render events with filtered results
  renderEventCards(filteredEvents, 'all-events-grid', false);
  
  // Show empty state if no matches found
  const emptyState = document.getElementById('events-empty');
  if (filteredEvents.length === 0 && searchTerm !== '') {
    const grid = document.getElementById('all-events-grid');
    const noResultsMsg = document.createElement('div');
    noResultsMsg.className = 'empty-state';
    noResultsMsg.style.gridColumn = '1/-1';
    noResultsMsg.innerHTML = `
      <div class="icon">🔍</div>
      <h3>No events found</h3>
      <p>No events match "<strong>${escHtml(searchTerm)}</strong>"</p>
    `;
    grid.appendChild(noResultsMsg);
  } else if (filteredEvents.length === 0) {
    emptyState.style.display = '';
  } else {
    emptyState.style.display = 'none';
  }
}

// ── UPLOAD ───────────────────────────────────────────────────────────────────
function populateEventSelect() {
  const sel = document.getElementById('upload-event-select');
  // Keep first option
  while (sel.options.length > 1) sel.remove(1);
  allEvents.forEach(ev => {
    const opt = new Option(`${ev.title} (${ev.photo_count} photos)`, ev.id);
    sel.add(opt);
  });
}

async function onEventSelect() {
  const evId = parseInt(document.getElementById('upload-event-select').value);
  selectedEventId = evId || null;

  document.getElementById('upload-zone-wrapper').style.display = evId ? '' : 'none';
  if (!evId) return;

  await refreshPhotos();
  await refreshIndexingStatus();
}

async function refreshPhotos() {
  if (!selectedEventId) return;
  const grid  = document.getElementById('photo-grid');
  const count = document.getElementById('event-photo-count');
  grid.innerHTML = '<div style="color:var(--white-30);padding:1rem;">Loading…</div>';

  try {
    const data = await Api.listPhotos(selectedEventId);
    count.textContent = `(${data.total})`;
    grid.innerHTML = '';
    
    if (data.photos.length === 0) {
      grid.innerHTML = '<p style="color:var(--white-30);padding:1rem;">No photos yet. Upload some above.</p>';
      document.getElementById('photos-pagination').style.display = 'none';
      return;
    }
    
    // Store all photos for pagination
    allLoadedPhotos = data.photos;
    photosDisplayedCount = 0;
    isPhotosExpanded = false;
    
    // Display initial batch
    displayPhotoBatch();
    updatePhotoPaginationUI();
    
  } catch (err) {
    grid.innerHTML = `<p style="color:var(--danger);">Failed to load photos.</p>`;
    document.getElementById('photos-pagination').style.display = 'none';
  }
}

function displayPhotoBatch() {
  const grid = document.getElementById('photo-grid');
  const startIdx = 0;
  const endIdx = isPhotosExpanded ? allLoadedPhotos.length : Math.min(PHOTOS_PER_PAGE, allLoadedPhotos.length);
  
  grid.innerHTML = '';
  
  for (let i = startIdx; i < endIdx; i++) {
    const p = allLoadedPhotos[i];
    const div = document.createElement('div');
    div.className = 'photo-thumb';
    div.innerHTML = `
      <img src="/api/photos/thumbnail/${selectedEventId}/${p.filename}" alt="" loading="lazy"
           onerror="this.src='data:image/svg+xml,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'100\\' height=\\'100\\'><rect fill=\\'%231a1a24\\'/></svg>'" />
      ${p.face_count > 0 ? `<div class="face-count">👤 ${p.face_count}</div>` : ''}
      <button class="delete-btn" onclick="requestDeletePhotoFromGrid(${p.id},this)">✕</button>`;
    grid.appendChild(div);
  }
  
  photosDisplayedCount = endIdx;
}

function updatePhotoPaginationUI() {
  const pagination = document.getElementById('photos-pagination');
  const btn = document.getElementById('btn-photos-toggle');
  const countInfo = document.getElementById('photos-count-info');
  
  if (allLoadedPhotos.length <= PHOTOS_PER_PAGE) {
    pagination.style.display = 'none';
    return;
  }
  
  pagination.style.display = 'block';
  
  if (isPhotosExpanded) {
    btn.textContent = '↑ See Less Photos';
    countInfo.textContent = `Showing all ${allLoadedPhotos.length} photos`;
  } else {
    btn.textContent = '📸 See More Photos';
    countInfo.textContent = `Showing ${PHOTOS_PER_PAGE} of ${allLoadedPhotos.length} photos`;
  }
}

function togglePhotosView() {
  isPhotosExpanded = !isPhotosExpanded;
  displayPhotoBatch();
  updatePhotoPaginationUI();
  
  setTimeout(() => {
    document.getElementById('photos-pagination').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, 100);
}

function loadMorePhotos() {
  togglePhotosView();
}

function loadLessPhotos() {
  togglePhotosView();
}

async function refreshIndexingStatus() {
  if (!selectedEventId) return;
  const box   = document.getElementById('indexing-status');
  const dot   = document.getElementById('indexing-dot');
  const label = document.getElementById('indexing-label');
  const fill  = document.getElementById('indexing-fill');
  const btn   = document.getElementById('btn-start-index');

  box.style.display = '';

  try {
    const data = await Api.indexingStatus(selectedEventId);
    if (data.is_indexed) {
      dot.className = 'indexing-dot';
      label.textContent = '✓ AI Indexing complete — Face recognition ready';
      fill.style.width = '100%';
      btn.style.display = 'none';
      clearInterval(indexingTimer);
    } else if (data.progress > 0) {
      dot.className = 'indexing-dot processing';
      label.textContent = `AI Indexing in progress… ${data.progress}%`;
      fill.style.width = data.progress + '%';
      btn.style.display = 'none';
      // Poll
      if (!indexingTimer) {
        indexingTimer = setInterval(refreshIndexingStatus, 3000);
      }
    } else {
      dot.className = 'indexing-dot';
      dot.style.background = 'var(--white-30)';
      label.textContent = `Not indexed — ${data.photo_count} photos need AI scanning`;
      fill.style.width = '0%';
      btn.style.display = '';
    }
  } catch { /* silent */ }
}

async function startIndexing() {
  if (!selectedEventId) return;
  try {
    await Api.startIndexing(selectedEventId);
    toast('AI Indexing started in background…', 'success');
    indexingTimer = setInterval(refreshIndexingStatus, 2500);
    await refreshIndexingStatus();
  } catch (err) {
    toast(err.message || 'Failed to start indexing', 'error');
  }
}

function setupDragDrop() {
  const zone = document.getElementById('upload-zone');
  if (!zone) return;
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    handleFiles(e.dataTransfer.files);
  });
}

function handleFiles(fileList) {
  uploadFiles_ = Array.from(fileList).filter(f => f.type.startsWith('image/'));
  if (!uploadFiles_.length) { toast('No valid image files selected', 'error'); return; }

  const queueDiv  = document.getElementById('upload-queue');
  const heading   = document.getElementById('queue-heading');
  const queueList = document.getElementById('queue-list');

  heading.textContent = `${uploadFiles_.length} file${uploadFiles_.length > 1 ? 's' : ''} ready to upload`;
  queueList.innerHTML = '';

  uploadFiles_.slice(0, 20).forEach(f => {
    const item = document.createElement('div');
    item.style.cssText = 'display:flex;align-items:center;gap:0.75rem;padding:0.5rem;background:var(--dark-mid);border-radius:6px;font-size:0.85rem;';
    item.innerHTML = `<span>🖼</span><span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escHtml(f.name)}</span><span style="color:var(--white-30);">${(f.size/1024/1024).toFixed(1)} MB</span>`;
    queueList.appendChild(item);
  });

  if (uploadFiles_.length > 20) {
    const more = document.createElement('p');
    more.style.cssText = 'text-align:center;color:var(--white-30);font-size:0.82rem;padding:0.5rem;';
    more.textContent = `… and ${uploadFiles_.length - 20} more files`;
    queueList.appendChild(more);
  }

  queueDiv.style.display = '';
}

function clearQueue() {
  uploadFiles_ = [];
  document.getElementById('upload-queue').style.display = 'none';
  document.getElementById('file-input').value = '';
}

async function uploadFiles() {
  if (!selectedEventId) { toast('Please select an event first', 'error'); return; }
  if (!uploadFiles_.length) { toast('No files selected', 'error'); return; }

  const btn  = document.getElementById('btn-upload');
  const fill = document.getElementById('upload-fill');
  btn.disabled = true; btn.textContent = 'Uploading…';
  document.getElementById('upload-progress-wrap').style.display = '';

  try {
    const data = await Api.uploadPhotos(selectedEventId, uploadFiles_, pct => {
      fill.style.width = pct + '%';
    });
    toast(`✓ ${data.message}`, 'success');
    clearQueue();
    await refreshPhotos();
    await refreshIndexingStatus();
    await loadOverview();
  } catch (err) {
    toast(err.message || 'Upload failed', 'error');
  } finally {
    btn.disabled = false; btn.textContent = '⬆ Upload All';
    document.getElementById('upload-progress-wrap').style.display = 'none';
    fill.style.width = '0%';
  }
}

async function deletePhotoFromGrid(photoId, btn) {
  if (!photoId || !btn) return;
  try {
    await Api.deletePhoto(photoId);
    btn.closest('.photo-thumb').remove();
    // Refresh photos to update pagination
    await refreshPhotos();
    toast('Photo deleted', 'success');
  } catch { toast('Delete failed', 'error'); }
}

let pendingDeletePhotoId = null;
let pendingDeletePhotoBtn = null;

function requestDeletePhotoFromGrid(photoId, btn) {
  pendingDeletePhotoId = photoId;
  pendingDeletePhotoBtn = btn;
  const modal = document.getElementById('delete-photo-modal');
  if (modal) modal.classList.add('active');
}

function closeDeletePhotoModal() {
  pendingDeletePhotoId = null;
  pendingDeletePhotoBtn = null;
  const modal = document.getElementById('delete-photo-modal');
  if (modal) modal.classList.remove('active');
}

async function confirmDeletePhoto() {
  if (!pendingDeletePhotoId || !pendingDeletePhotoBtn) return;

  const photoId = pendingDeletePhotoId;
  const btn = pendingDeletePhotoBtn;
  const confirmBtn = document.getElementById('btn-confirm-delete-photo');

  if (confirmBtn) {
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Deleting...';
  }

  try {
    await deletePhotoFromGrid(photoId, btn);
    closeDeletePhotoModal();
  } catch {
    toast('Delete failed', 'error');
  } finally {
    if (confirmBtn) {
      confirmBtn.disabled = false;
      confirmBtn.textContent = 'Delete';
    }
  }
}

// ── CREATE EVENT ──────────────────────────────────────────────────────────────
function openCreateEvent() {
  document.getElementById('create-event-modal').classList.add('active');
}
function closeCreateEvent() {
  document.getElementById('create-event-modal').classList.remove('active');
}

function setupPublicToggle() {
  const sel = document.getElementById('ev-public');
  if (sel) sel.addEventListener('change', () => {
    document.getElementById('pin-group').style.display = sel.value === 'false' ? '' : 'none';
  });
}

async function handleCreateEvent(e) {
  e.preventDefault();
  
  const btn  = document.getElementById('btn-create-event');
  const body = {
    title:      document.getElementById('ev-title').value,
    description:document.getElementById('ev-desc').value,
    event_date: document.getElementById('ev-date').value || null,
    event_type: document.getElementById('ev-type').value || 'general',
    is_public:  document.getElementById('ev-public').value === 'true',
    access_pin: document.getElementById('ev-pin').value || null
  };

  btn.disabled = true; btn.textContent = 'Creating…';
  try {
    const response = await Api.createEvent(body);
    
    toast('✓ Event created successfully!', 'success');
    closeCreateEvent();
    await loadEvents();
    await loadOverview();
    document.getElementById('ev-title').value = '';
    document.getElementById('ev-desc').value = '';
  } catch (err) {
    toast(err.message || 'Failed to create event', 'error');
  } finally {
    btn.disabled = false; btn.textContent = 'Create Event';
  }
}

// ── EVENT DETAIL ──────────────────────────────────────────────────────────────
async function openEventDetail(eventId) {
  const detailSection = document.getElementById('section-event-detail');
  const body  = document.getElementById('event-detail-content');
  if (!detailSection || !body) return;

  const currentSection = Array.from(document.querySelectorAll('.dash-section'))
    .find(section => getComputedStyle(section).display !== 'none' && section.id !== 'section-event-detail');
  previousSectionBeforeDetail = currentSection
    ? currentSection.id.replace('section-', '')
    : 'events';

  document.querySelectorAll('.dash-section').forEach(section => {
    section.style.display = 'none';
  });
  detailSection.style.display = '';

  body.innerHTML = '<div style="text-align:center;padding:2rem;"><div class="spinner" style="margin:0 auto;"></div></div>';
  window.scrollTo({ top: 0, behavior: 'smooth' });

  try {
    const data = await Api.eventStats(eventId);
    const ev = data.event;
    const publicGalleryUrl = `${window.location.origin}/gallery/${encodeURIComponent(ev.slug)}`;
    const manageGalleryUrl = `${publicGalleryUrl}?from=event-detail&eventId=${encodeURIComponent(ev.id)}`;
    const dateStr = ev.event_date
      ? new Date(ev.event_date).toLocaleDateString('en-IN', { day:'numeric', month:'long', year:'numeric' })
      : 'Not set';

    body.innerHTML = `
      <button class="btn btn-ghost btn-sm" onclick="closeEventDetail()" style="margin-bottom:1.5rem;">← Back</button>
      <div class="badge ${ev.is_indexed ? 'badge-green' : 'badge-red'}" style="margin-bottom:1rem;">
        ${ev.is_indexed ? '✓ AI Indexed' : '⚠ Not Indexed'}
      </div>
      <h2 style="margin-bottom:0.4rem;">${escHtml(ev.title)}</h2>
      <p style="margin-bottom:1.5rem;">${ev.description ? escHtml(ev.description) : '<em>No description</em>'}</p>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem;">
        <div class="card card-sm" style="text-align:center;">
          <div style="font-family:var(--font-display);font-size:2rem;font-weight:800;color:var(--gold);">${data.total_photos}</div>
          <div style="font-size:0.8rem;color:var(--white-30);">Total Photos</div>
        </div>
        <div class="card card-sm" style="text-align:center;">
          <div style="font-family:var(--font-display);font-size:2rem;font-weight:800;color:var(--gold);">${data.total_faces}</div>
          <div style="font-size:0.8rem;color:var(--white-30);">Faces Indexed</div>
        </div>
      </div>

      <div style="display:flex;flex-direction:column;gap:0.5rem;font-size:0.88rem;color:var(--white-60);margin-bottom:1.5rem;">
        <div>📅 Event Date: ${dateStr}</div>
        <div>${ev.is_public ? '🔓 Public gallery' : '🔒 Private — PIN protected'}</div>
        <div>🤖 Processed: ${data.processed} / ${data.total_photos} photos</div>
      </div>

      <div style="background:var(--dark-mid);border:1px solid var(--border);border-radius:var(--radius);padding:1rem;margin-bottom:1.5rem;">
        <div style="font-size:0.78rem;color:var(--white-30);margin-bottom:0.4rem;text-transform:uppercase;letter-spacing:0.06em;">Gallery Link</div>
        <div style="display:flex;align-items:center;gap:0.75rem;">
          <code style="flex:1;font-size:0.82rem;color:var(--gold);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${publicGalleryUrl}</code>
          <button class="btn btn-sm btn-ghost" onclick="copyLink('${publicGalleryUrl}')">Copy</button>
        </div>
      </div>

      <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
        <a href="${manageGalleryUrl}" class="btn btn-gold btn-sm">Open Gallery ↗</a>
        <button class="btn btn-ghost btn-sm" onclick="switchToUpload(${ev.id});">Upload Photos</button>
        <button class="btn btn-ghost btn-sm" onclick="openSelectCoverModal(${ev.id})">🖼 Set Cover Photo</button>
        ${!ev.is_indexed ? `<button class="btn btn-ghost btn-sm" onclick="startIndexingFromDetail(${ev.id})">🤖 Start Indexing</button>` : ''}
      </div>`;
  } catch (err) {
    body.innerHTML = `<p style="color:var(--danger);">Failed to load event details.</p>`;
  }
}

function closeEventDetail() {
  const targetTab = previousSectionBeforeDetail || 'events';
  switchSection(targetTab);
}

// ── SELECT EVENT COVER PHOTO ───────────────────────────────────────────────────
async function openSelectCoverModal(eventId) {
  const modal = document.getElementById('select-cover-modal');
  const container = document.getElementById('select-cover-content');
  
  // Find the current event to display info
  let event = allEvents.find(e => e.id === eventId);
  if (!event) {
    // Try to load the event from API if not in cache
    try {
      const response = await Api.request('GET', `/events/${eventId}`);
      event = response;  // Backend returns event object directly, not wrapped
    } catch (err) {
      toast('Event not found', 'error');
      return;
    }
  }
  
  container.innerHTML = '<div style="text-align:center;padding:2rem;"><div class="spinner" style="margin:0 auto;"></div></div>';
  modal.classList.add('active');
  
  try {
    const photos = await Api.listPhotos(eventId);
    
    if (!photos.photos || photos.photos.length === 0) {
      container.innerHTML = `
        <button class="btn btn-ghost btn-sm" onclick="closeSelectCoverModal()" style="margin-bottom:1.5rem;">← Back</button>
        <h2 style="margin-bottom:1rem;">Select Cover Photo</h2>
        <p style="color:var(--white-30);">No photos in this event yet. Upload some photos first.</p>`;
      return;
    }
    
    // Build photo grid HTML with adjustment buttons
    let photosHTML = photos.photos.map(photo => `
      <div style="position:relative;border-radius:var(--radius);overflow:hidden;background:rgba(0,0,0,0.3);border:3px solid transparent;transition:all 0.3s ease;${event.cover_image === photo.filename ? 'border-color:var(--gold);' : ''}" class="photo-item-wrapper" data-event-id="${eventId}" data-photo-id="${photo.id}" data-filename="${photo.filename}">
        <img src="/api/photos/thumbnail/${eventId}/${photo.filename}" alt="" style="width:100%;height:100%;object-fit:cover;aspect-ratio:1;cursor:pointer;" onclick="setCoverPhoto(${eventId}, ${photo.id}, this.parentElement)" />
        ${event.cover_image === photo.filename ? '<div style="position:absolute;inset:0;background:rgba(212,175,55,0.2);display:flex;align-items:center;justify-content:center;"><div style="font-size:2rem;text-shadow:0 2px 4px rgba(0,0,0,0.5);">✓</div></div>' : ''}
        
        <div style="position:absolute;bottom:0;left:0;right:0;background:linear-gradient(to top, rgba(0,0,0,0.8), transparent);padding:0.75rem;display:flex;gap:0.5rem;opacity:0;transition:opacity 0.3s ease;pointer-events:none;" class="photo-actions">
          <button class="btn btn-gold btn-sm" style="flex:1;pointer-events:auto;" onclick="event.stopPropagation(); const wrapper = this.closest('.photo-item-wrapper'); openPhotoAdjustmentModal(wrapper.dataset.eventId, wrapper.dataset.photoId, wrapper.dataset.filename)">✏️ Adjust</button>
        </div>
      </div>
    `).join('');
    
    // Add CSS to show actions on hover
    const style = document.createElement('style');
    style.textContent = `
      .photo-item-wrapper:hover .photo-actions {
        opacity: 1 !important;
      }
    `;
    document.head.appendChild(style);
    
    container.innerHTML = `
      <button class="btn btn-ghost btn-sm" onclick="closeSelectCoverModal()" style="margin-bottom:1.5rem;">← Back</button>
      <h2 style="margin-bottom:0.5rem;">Select Cover Photo</h2>
      <p style="color:var(--white-60);margin-bottom:1.5rem;">Click a photo to set as cover · Hover to adjust</p>
      
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:1rem;max-height:60vh;overflow-y:auto;">
        ${photosHTML}
      </div>`;
      
  } catch (err) {
    container.innerHTML = `<p style="color:var(--danger);">Failed to load photos for this event.</p>`;
  }
}

function closeSelectCoverModal() {
  document.getElementById('select-cover-modal').classList.remove('active');
}

async function setCoverPhoto(eventId, photoId, element) {
  try {
    
    // Highlight the selected photo
    document.querySelectorAll('.photo-item-wrapper').forEach(el => {
      el.style.borderColor = 'transparent';
      const checkmark = el.querySelector('div[style*="rgba(212,175"]');
      if (checkmark) checkmark.remove();
    });
    
    element.style.borderColor = 'var(--gold)';
    element.innerHTML += '<div style="position:absolute;inset:0;background:rgba(212,175,55,0.2);display:flex;align-items:center;justify-content:center;"><div style="font-size:2rem;text-shadow:0 2px 4px rgba(0,0,0,0.5);">✓</div></div>';
    
    const result = await Api.setCoverPhoto(eventId, photoId);
    toast('Cover photo updated! 🎉', 'success');
    
    // Update the events in memory with new cover image
    const eventIndex = allEvents.findIndex(e => e.id === eventId);
    if (eventIndex !== -1) {
      allEvents[eventIndex] = result.event;
    }
    
    // Refresh the event cards
    await loadEvents();
    
    // Close modal after a short delay
    setTimeout(() => {
      closeSelectCoverModal();
    }, 800);
    
  } catch (err) {
    toast('Error setting cover photo: ' + (err.message || 'Unknown error'), 'error');
  }
}

function copyLink(url) {
  navigator.clipboard.writeText(url).then(() => toast('Link copied!', 'success'));
}

function shareButtonClicked(button) {
  const galleryUrl = button.getAttribute('data-gallery-url');
  const eventTitle = button.getAttribute('data-event-title');
  
  if (!galleryUrl || !eventTitle) {
    toast('Error: Missing event information', 'error');
    return;
  }
  
  openShareModal(galleryUrl, eventTitle);
}

function openShareModal(galleryUrl, eventTitle) {
  const section = document.getElementById('section-share');
  const content = document.getElementById('share-page-content');

  if (!section || !content) {
    toast('Error: Share page not found', 'error');
    return;
  }

  const fullUrl = `${window.location.origin}${galleryUrl}`;
  const currentSection = Array.from(document.querySelectorAll('.dash-section'))
    .find(sectionEl => getComputedStyle(sectionEl).display !== 'none' && sectionEl.id !== 'section-share');
  previousSectionBeforeShare = currentSection
    ? currentSection.id.replace('section-', '')
    : 'events';

  content.innerHTML = `
    <button class="btn btn-ghost btn-sm" onclick="closeShareModal()" style="margin-bottom:1.5rem;">← Back</button>
    <div class="badge badge-green" style="margin-bottom:1rem;">Share Gallery</div>
    <h2 style="margin-bottom:0.5rem;">Share &ldquo;${escHtml(eventTitle)}&rdquo;</h2>
    <p style="color:var(--white-60); margin-bottom:1.5rem;">Send this link to your clients to view the photos:</p>

    <div style="background:var(--dark-mid);border:1px solid var(--border);border-radius:var(--radius);padding:1rem;margin-bottom:1.5rem;">
      <div style="font-size:0.75rem;color:var(--white-30);margin-bottom:0.5rem;text-transform:uppercase;letter-spacing:0.06em;">Gallery Link</div>
      <div class="share-input-group">
        <input type="text" value="${fullUrl}" readonly id="share-url-input" style="flex:1;background:var(--black);border:1px solid var(--border);border-radius:6px;padding:0.75rem;color:var(--gold);font-family:monospace;font-size:0.85rem;">
        <button class="btn btn-gold btn-sm" onclick="copyShareLink()" style="white-space:nowrap;">📋 Copy</button>
      </div>
    </div>

    <div style="margin-bottom:1.5rem;">
      <p style="color:var(--white-30);font-size:0.85rem;margin-bottom:1rem;">Share on social media:</p>
      <div class="share-social-buttons" style="display:flex;gap:0.75rem;flex-wrap:wrap;">
        <a href="https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(fullUrl)}" target="_blank" style="background:#1877F2;color:white;padding:0.5rem 1rem;border-radius:6px;text-decoration:none;font-weight:600;font-size:0.82rem;transition:all 0.3s ease;border:none;cursor:pointer;">📘 Facebook</a>
        <a href="https://twitter.com/intent/tweet?url=${encodeURIComponent(fullUrl)}&text=${encodeURIComponent('Check out my photos')}" target="_blank" style="background:#1DA1F2;color:white;padding:0.5rem 1rem;border-radius:6px;text-decoration:none;font-weight:600;font-size:0.82rem;transition:all 0.3s ease;border:none;cursor:pointer;">𝕏 Twitter</a>
        <a href="https://wa.me/?text=${encodeURIComponent('Check out my photos: ' + fullUrl)}" target="_blank" style="background:#25D366;color:white;padding:0.5rem 1rem;border-radius:6px;text-decoration:none;font-weight:600;font-size:0.82rem;transition:all 0.3s ease;border:none;cursor:pointer;">💬 WhatsApp</a>
        <a href="mailto:?subject=${encodeURIComponent('Check out my photos')}&body=${encodeURIComponent('View my photos here: ' + fullUrl)}" style="background:var(--gold);color:#1a1a2e;padding:0.5rem 1rem;border-radius:6px;text-decoration:none;font-weight:600;font-size:0.82rem;transition:all 0.3s ease;border:none;cursor:pointer;">✉️ Email</a>
      </div>
    </div>

    <button class="btn btn-ghost" onclick="closeShareModal()" style="width:100%;">Close</button>
  `;
  
  document.querySelectorAll('.dash-section').forEach(sectionEl => {
    sectionEl.style.display = 'none';
  });
  section.style.display = '';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function closeShareModal() {
  const targetTab = previousSectionBeforeShare || 'events';
  switchSection(targetTab);
}

function copyShareLink() {
  const input = document.getElementById('share-url-input');
  if (!input) {
    toast('Error copying link', 'error');
    return;
  }
  navigator.clipboard.writeText(input.value).then(() => {
    toast('Link copied to clipboard!', 'success');
  }).catch((err) => {
    toast('Failed to copy link', 'error');
  });
}

async function startIndexingFromDetail(eventId) {
  try {
    await Api.startIndexing(eventId);
    toast('AI Indexing started!', 'success');
    closeEventDetail();
  } catch (err) {
    toast(err.message || 'Failed to start indexing', 'error');
  }
}

function switchToUpload(eventId) {
  switchSection('upload');
  document.getElementById('upload-event-select').value = eventId;
  onEventSelect();
}

// ── DELETE EVENT ──────────────────────────────────────────────────────────────
let pendingDeleteEventName = null;

function deleteEvent(eventId, eventName, e) {
  e.stopPropagation();
  pendingDeleteEventId = eventId;
  pendingDeleteEventName = eventName;
  const modal = document.getElementById('delete-event-modal');
  const modalText = modal.querySelector('p');
  if (modalText) modalText.textContent = `Are you sure you want to delete "${eventName}"?`;
  if (modal) modal.classList.add('active');
}

function closeDeleteEventModal() {
  pendingDeleteEventId = null;
  pendingDeleteEventName = null;
  const modal = document.getElementById('delete-event-modal');
  if (modal) modal.classList.remove('active');
}

async function confirmDeleteEvent() {
  if (!pendingDeleteEventId) return;

  const eventId = pendingDeleteEventId;
  const btn = document.getElementById('btn-confirm-delete-event');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Deleting...';
  }

  try {
    await Api.deleteEvent(eventId);
    closeDeleteEventModal();
    toast('Event deleted', 'success');
    await loadEvents();
    await loadOverview();
  } catch (err) {
    toast(err.message || 'Delete failed', 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Delete';
    }
  }
}

// ── SETTINGS ─────────────────────────────────────────────────────────────────
function loadSettings() {
  if (photographer.name)        document.getElementById('set-name').value       = photographer.name;
  if (photographer.brand_color) document.getElementById('set-color').value      = photographer.brand_color;
  if (photographer.watermark)   document.getElementById('set-watermark').value  = photographer.watermark;

  const themeSelect = document.getElementById('set-theme');
  if (themeSelect) {
    themeSelect.value = getSavedTheme();
    if (!themeSelect.dataset.bound) {
      themeSelect.addEventListener('change', function() {
        saveTheme(this.value);
      });
      themeSelect.dataset.bound = '1';
    }
  }
}

async function saveSettings() {
  try {
    const themeSelect = document.getElementById('set-theme');
    if (themeSelect) {
      saveTheme(themeSelect.value);
    }

    const data = await Api.updateProfile({
      name:        document.getElementById('set-name').value,
      brand_color: document.getElementById('set-color').value,
      watermark:   document.getElementById('set-watermark').value
    });
    photographer = data.photographer;
    Api.savePhotographer(photographer);
    setupSidebarUser();
    toast('Settings saved!', 'success');
  } catch (err) {
    toast(err.message || 'Failed to save settings', 'error');
  }
}

// ── AUTH ──────────────────────────────────────────────────────────────────────
function logout() {
  Api.clearToken();
  window.location.href = '/login';
}

// ── PHOTO ADJUSTMENT ──────────────────────────────────────────────────────────
let photoAdjustmentState = {
  cropper: null,
  eventId: null,
  photoId: null,
  photoFilename: null,
  rotation: 0
};

async function openPhotoAdjustmentModal(eventId, photoId, photoFilename) {
  try {
    photoAdjustmentState.eventId = eventId;
    photoAdjustmentState.photoId = photoId;
    photoAdjustmentState.photoFilename = photoFilename;
    photoAdjustmentState.rotation = 0;
    
    const imageUrl = `/api/photos/thumbnail/${eventId}/${photoFilename}`;
    const imgElement = document.getElementById('adjustment-image');
    
    // Clean up old cropper if exists
    if (photoAdjustmentState.cropper) {
      photoAdjustmentState.cropper.destroy();
      photoAdjustmentState.cropper = null;
    }
    
    imgElement.src = imageUrl;
    imgElement.onload = function() {
      // Create new cropper instance
      photoAdjustmentState.cropper = new Cropper(imgElement, {
        aspectRatio: 0,
        viewMode: 1,
        autoCropArea: 1,
        responsive: true,
        restore: true,
        guides: true,
        center: true,
        highlight: true,
        cropBoxMovable: true,
        cropBoxResizable: true,
        toggleDragModeOnDblclick: true,
        minCanvasWidth: 100,
        minCanvasHeight: 100,
        minCropBoxWidth: 50,
        minCropBoxHeight: 50,
        background: false
      });
      
      // Reset controls
      document.getElementById('crop-zoom').value = 1;
      document.getElementById('zoom-value').textContent = '100%';
      document.querySelectorAll('.aspect-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelector('.aspect-btn[data-ratio="0"]').classList.add('active');
    };
    
    document.getElementById('photo-adjustment-modal').classList.add('active');
  } catch (err) {
    toast('Error opening photo editor: ' + (err.message || 'Unknown error'), 'error');
  }
}

function closePhotoAdjustmentModal() {
  if (photoAdjustmentState.cropper) {
    photoAdjustmentState.cropper.destroy();
    photoAdjustmentState.cropper = null;
  }
  photoAdjustmentState.rotation = 0;
  document.getElementById('photo-adjustment-modal').classList.remove('active');
}

function updateCropZoom() {
  const zoomValue = parseFloat(document.getElementById('crop-zoom').value);
  if (photoAdjustmentState.cropper) {
    photoAdjustmentState.cropper.setCanvasData({
      left: 0,
      top: 0,
      width: photoAdjustmentState.cropper.getCanvasData().width,
      height: photoAdjustmentState.cropper.getCanvasData().height
    });
    photoAdjustmentState.cropper.zoomTo(zoomValue);
  }
  document.getElementById('zoom-value').textContent = Math.round(zoomValue * 100) + '%';
}

function setCropAspect(button, ratio) {
  if (photoAdjustmentState.cropper) {
    photoAdjustmentState.cropper.setAspectRatio(ratio);
  }
  
  // Update button styles
  document.querySelectorAll('.aspect-btn').forEach(btn => btn.classList.remove('active'));
  button.classList.add('active');
}

function rotateImageLeft() {
  if (photoAdjustmentState.cropper) {
    photoAdjustmentState.cropper.rotate(-45);
    photoAdjustmentState.rotation -= 45;
  }
}

function rotateImageRight() {
  if (photoAdjustmentState.cropper) {
    photoAdjustmentState.cropper.rotate(45);
    photoAdjustmentState.rotation += 45;
  }
}

async function applyCropAndSetCover() {
  try {
    if (!photoAdjustmentState.cropper) {
      toast('Error: Cropper not initialized', 'error');
      return;
    }
    
    const button = document.getElementById('btn-apply-crop');
    button.disabled = true;
    button.textContent = '⏳ Applying...';
    
    // Get the cropped canvas
    const canvas = photoAdjustmentState.cropper.getCroppedCanvas({
      maxWidth: 1920,
      maxHeight: 1080,
      fillColor: '#fff',
      imageSmoothingEnabled: true,
      imageSmoothingQuality: 'high'
    });
    
    // Wrap canvas to blob in a promise for better async handling
    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (blob) resolve(blob);
        else reject(new Error('Failed to create image blob'));
      }, 'image/jpeg', 0.95);
    });
    
    // Create FormData with the cropped image
    const formData = new FormData();
    formData.append('image', blob, photoAdjustmentState.photoFilename);
    
    // Get the authorization token
    const token = Api.getToken();
    
    if (!token) {
      throw new Error('Authentication token not found. Please login again.');
    }
    
    // Upload the cropped image with proper authentication
    const response = await fetch(`/api/photos/update/${photoAdjustmentState.eventId}/${photoAdjustmentState.photoId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData,
      credentials: 'include'
    });
    
    const responseData = await response.json();
    
    if (!response.ok) {
      throw new Error(responseData.error || `Upload failed: ${response.statusText}`);
    }
    
    toast('Photo adjusted successfully! 📸', 'success');
    
    // Now automatically set the adjusted photo as cover
    const setCoverResult = await Api.setCoverPhoto(photoAdjustmentState.eventId, photoAdjustmentState.photoId);
    
    // Update the event in allEvents
    const eventIndex = allEvents.findIndex(e => e.id === photoAdjustmentState.eventId);
    if (eventIndex !== -1) {
      allEvents[eventIndex] = setCoverResult.event;
    }
    
    toast('Cover photo updated! 🎉', 'success');
    
    // Close modals
    closePhotoAdjustmentModal();
    closeSelectCoverModal();
    
    // Refresh the event cards to show new cover
    await loadEvents();
    
  } catch (err) {
    toast('Error: ' + (err.message || 'Unknown error'), 'error');
  } finally {
    const button = document.getElementById('btn-apply-crop');
    if (button) {
      button.disabled = false;
      button.textContent = '✓ Apply & Set Cover';
    }
  }
}

// ── EDIT EVENT ─────────────────────────────────────────────────────────────
let editingEventId = null;

async function openEditEventModal(eventId) {
  try {
    const event = allEvents.find(e => e.id === eventId);
    if (!event) {
      toast('Event not found', 'error');
      return;
    }
    
    // Populate form with event data
    document.getElementById('edit-event-title').value = event.title || '';
    document.getElementById('edit-event-type').value = event.event_type || 'general';
    document.getElementById('edit-event-description').value = event.description || '';
    
    // Format date for input
    if (event.event_date) {
      const dateObj = new Date(event.event_date);
      const year = dateObj.getFullYear();
      const month = String(dateObj.getMonth() + 1).padStart(2, '0');
      const day = String(dateObj.getDate()).padStart(2, '0');
      document.getElementById('edit-event-date').value = `${year}-${month}-${day}`;
    }
    
    editingEventId = eventId;
    
    // Open modal
    document.getElementById('edit-event-modal').classList.add('active');
    
  } catch (err) {
    toast('Error opening edit form: ' + (err.message || 'Unknown error'), 'error');
  }
}

function closeEditEventModal() {
  document.getElementById('edit-event-modal').classList.remove('active');
  editingEventId = null;
  document.getElementById('edit-event-form').reset();
}

async function saveEventChanges() {
  try {
    if (!editingEventId) {
      toast('No event selected', 'error');
      return;
    }
    
    const title = document.getElementById('edit-event-title').value.trim();
    const event_type = document.getElementById('edit-event-type').value;
    const event_date = document.getElementById('edit-event-date').value;
    const description = document.getElementById('edit-event-description').value.trim();
    
    if (!title) {
      toast('Event title is required', 'error');
      return;
    }
    
    const data = {
      title,
      event_type,
      event_date,
      description
    };
    
    const result = await Api.request('PUT', `/events/${editingEventId}`, data);
    
    // Update in allEvents
    const eventIndex = allEvents.findIndex(e => e.id === editingEventId);
    if (eventIndex !== -1) {
      allEvents[eventIndex] = result.event;
    }
    
    toast('Event updated successfully! ✅', 'success');
    
    // Close modal and reload
    closeEditEventModal();
    await loadEvents();
    
  } catch (err) {
    toast('Error: ' + (err.message || 'Failed to save event'), 'error');
  }
}

// Attach form submit handler
document.addEventListener('DOMContentLoaded', function() {
  const form = document.getElementById('edit-event-form');
  if (form) {
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      saveEventChanges();
    });
  }

  const deleteModal = document.getElementById('delete-event-modal');
  if (deleteModal) {
    deleteModal.addEventListener('click', function(e) {
      if (e.target === deleteModal) closeDeleteEventModal();
    });
  }

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      const modal = document.getElementById('delete-event-modal');
      if (modal && modal.classList.contains('active')) {
        closeDeleteEventModal();
      }
    }
  });
});

// ── Utils ─────────────────────────────────────────────────────────────────────
function escHtml(str) {
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(str || ''));
  return d.innerHTML;
}

// ── PHOTOGRAPHER PROFILE ──────────────────────────────────────────────────────
function switchProfileTab(tabName) {
  // Hide all tabs
  document.getElementById('profile-tab-about').style.display = 'none';
  document.getElementById('profile-tab-photography').style.display = 'none';
  document.getElementById('profile-tab-chats').style.display = 'none';
  
  // Remove active from all buttons
  document.querySelectorAll('.profile-tab-btn').forEach(btn => btn.classList.remove('active'));
  
  // Show selected tab
  document.getElementById(`profile-tab-${tabName}`).style.display = '';
  const activeBtnId = tabName === 'about'
    ? 'profile-tab-btn-about'
    : (tabName === 'photography' ? 'profile-tab-btn-photography' : 'profile-tab-btn-chats');
  const activeBtn = document.getElementById(activeBtnId);
  if (activeBtn) activeBtn.classList.add('active');
  
  // Load data if photography tab
  if (tabName === 'photography') {
    loadPhotographyInfo();
    loadPortfolioPhotos();
  } else if (tabName === 'about') {
    loadContactInfo();
  } else if (tabName === 'chats') {
    initProfileChat();
  }
}

async function initProfileChat() {
  const box = document.getElementById('profile-chat-messages');
  const input = document.getElementById('profile-chat-input');
  if (!box) return;

  if (!profileChatMessages.length) {
    try {
      const data = await Api.getProfileChatMessages();
      profileChatMessages = Array.isArray(data.messages) ? data.messages : [];
    } catch (err) {
      profileChatMessages = [];
    }

    if (!profileChatMessages.length) {
      profileChatMessages = [{
        role: 'client',
        text: 'Hi photographer, can you share the latest portfolio previews for my event?'
      }];
    }
  }

  if (input && !input.dataset.boundEnter) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        sendProfileChatMessage();
      }
    });
    input.dataset.boundEnter = '1';
  }

  const sender = document.getElementById('profile-chat-sender');
  if (sender && !sender.value) sender.value = 'photographer';

  renderProfileChat();
}

function renderProfileChat() {
  const box = document.getElementById('profile-chat-messages');
  if (!box) return;

  box.innerHTML = '';

  profileChatMessages.forEach(msg => {
    const row = document.createElement('div');
    const msgRole = (msg.role || '').toLowerCase();
    let cssRole = 'client';
    if (msgRole === 'photographer' || msgRole === 'user') cssRole = 'photographer';
    if (msgRole === 'client' || msgRole === 'assistant') cssRole = 'client';

    row.className = `profile-chat-msg ${cssRole}`;
    row.textContent = msg.text || '';
    box.appendChild(row);
  });

  box.scrollTop = box.scrollHeight;
}

async function sendProfileChatMessage() {
  const input = document.getElementById('profile-chat-input');
  const senderEl = document.getElementById('profile-chat-sender');
  if (!input) return;

  const text = input.value.trim();
  const sender = senderEl?.value === 'client' ? 'client' : 'photographer';
  if (!text) return;

  input.value = '';

  try {
    const data = await Api.sendProfileChatMessage(text, sender);
    profileChatMessages = Array.isArray(data.messages) ? data.messages : profileChatMessages;
  } catch (err) {
    // If API call fails, keep local optimistic echo
    profileChatMessages.push({ role: sender, text });
    profileChatMessages.push({ role: 'client', text: 'Server sync failed. Please try again.' });
    toast('Chat sync failed. Showing local message only.', 'error');
  }

  renderProfileChat();
}

function openProfileChatFromLN() {
  switchSection('profile');
  switchProfileTab('chats');
  initProfileChat();

  const card = document.getElementById('profile-chat-card');
  if (card) {
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function openAddSpecializationModal() {
  const modal = document.getElementById('specialization-modal');
  const input = document.getElementById('specialization-name');
  if (!modal || !input) return;

  modal.classList.add('active');
  input.value = '';
  setTimeout(() => input.focus(), 0);
}

function closeAddSpecializationModal() {
  const modal = document.getElementById('specialization-modal');
  if (!modal) return;

  modal.classList.remove('active');
}

let pendingSpecializationRemoval = [];
let pendingPortfolioPhotoRemoval = null;

function openRemoveSpecializationModal(names) {
  const modal = document.getElementById('specialization-remove-modal');
  const message = document.getElementById('specialization-remove-message');
  if (!modal || !message) return;

  pendingSpecializationRemoval = Array.isArray(names) ? names.slice() : [];
  message.textContent = pendingSpecializationRemoval.length === 1
    ? `Remove event ${pendingSpecializationRemoval[0]}?`
    : `Remove event ${pendingSpecializationRemoval.join(', ')}?`;
  modal.classList.add('active');
}

function closeRemoveSpecializationModal() {
  const modal = document.getElementById('specialization-remove-modal');
  if (!modal) return;

  modal.classList.remove('active');
}

function confirmRemoveSpecialization() {
  if (!pendingSpecializationRemoval.length) {
    closeRemoveSpecializationModal();
    return;
  }

  const optionsWrap = document.getElementById('specialization-options');
  if (!optionsWrap) {
    toast('Specializations section not found', 'error');
    closeRemoveSpecializationModal();
    return;
  }

  pendingSpecializationRemoval.forEach(name => {
    const checkbox = Array.from(optionsWrap.querySelectorAll('.spec-checkbox')).find(cb => cb.value === name);
    const label = checkbox?.closest('label');
    if (label) label.remove();
  });

  const removedCount = pendingSpecializationRemoval.length;
  pendingSpecializationRemoval = [];
  closeRemoveSpecializationModal();
  toast(removedCount === 1 ? 'Event removed' : `${removedCount} events removed`, 'success');
}

function openPortfolioPhotoRemoveModal(photo) {
  const modal = document.getElementById('portfolio-photo-remove-modal');
  const message = document.getElementById('portfolio-photo-remove-message');
  if (!modal || !message || !photo) return;

  pendingPortfolioPhotoRemoval = photo;
  message.textContent = 'Are you sure you want to remove this photo from portfolio?';
  modal.classList.add('active');
}

function closePortfolioPhotoRemoveModal() {
  const modal = document.getElementById('portfolio-photo-remove-modal');
  if (!modal) return;

  pendingPortfolioPhotoRemoval = null;
  modal.classList.remove('active');
}

async function confirmRemovePortfolioPhoto() {
  if (!pendingPortfolioPhotoRemoval) {
    closePortfolioPhotoRemoveModal();
    return;
  }

  const photoToRemove = pendingPortfolioPhotoRemoval;
  closePortfolioPhotoRemoveModal();

  try {
    await Api.removeSpecialPhoto(photoToRemove.id);
    const updatedProfile = await Api.getProfile();
    photographer = updatedProfile;
    Api.savePhotographer(photographer);
    await loadPortfolioPhotos();
    toast('Photo removed from portfolio', 'success');
  } catch (err) {
    toast('Error: ' + (err.message || 'Failed to remove photo'), 'error');
  }
}

function confirmAddSpecialization(event) {
  event.preventDefault();

  const optionsWrap = document.getElementById('specialization-options');
  const input = document.getElementById('specialization-name');
  if (!optionsWrap || !input) {
    toast('Specializations section not found', 'error');
    return;
  }

  const eventName = input.value.trim().replace(/\s+/g, ' ');
  if (!eventName) {
    toast('Event name cannot be empty', 'error');
    return;
  }

  const existing = Array.from(optionsWrap.querySelectorAll('.spec-checkbox')).some(cb => cb.value.toLowerCase() === eventName.toLowerCase());
  if (existing) {
    toast('This event already exists', 'info');
    return;
  }

  const label = document.createElement('label');
  label.style.cssText = 'display:flex;align-items:center;gap:0.5rem;';

  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.className = 'spec-checkbox';
  checkbox.value = eventName;
  checkbox.checked = true;

  label.appendChild(checkbox);
  label.append(' ' + eventName);
  optionsWrap.appendChild(label);

  closeAddSpecializationModal();
  toast('Event added successfully', 'success');
}

function removeSpecializationEvent() {
  const optionsWrap = document.getElementById('specialization-options');
  if (!optionsWrap) {
    toast('Specializations section not found', 'error');
    return;
  }

  const selected = Array.from(optionsWrap.querySelectorAll('.spec-checkbox:checked'));
  if (!selected.length) {
    toast('Select event checkbox first, then click Remove', 'info');
    return;
  }

  const selectedNames = selected.map(cb => cb.value).join(', ');
  openRemoveSpecializationModal(selected.map(cb => cb.value));
}

function toggleAboutEditMode(button) {
  if (!button) return;

  const currentEditing = button.dataset.editing === 'true';
  const nextEditing = !currentEditing;

  button.dataset.editing = nextEditing ? 'true' : 'false';
  button.innerHTML = nextEditing ? '🔒 Editing' : '✏️ Editable';
  button.style.background = nextEditing ? 'rgba(212,175,85,0.18)' : 'rgba(212,175,85,0.08)';
  button.style.borderColor = nextEditing ? 'rgba(212,175,85,0.55)' : 'rgba(212,175,85,0.35)';

  const inputs = document.querySelectorAll('#profile-tab-about input');
  inputs.forEach(input => {
    input.disabled = !nextEditing;
    input.style.opacity = nextEditing ? '1' : '0.72';
  });

  toast(nextEditing ? 'Contact editing enabled' : 'Contact editing locked', 'info');
}

async function loadContactInfo() {
  try {
    await loadPhotographerProfile();

    const profile = photographer; // Already loaded in state
    document.getElementById('profile-name').value = profile.name || '';
    document.getElementById('profile-email').value = profile.email || '';
    document.getElementById('profile-mobile').value = profile.mobile_number || '';
  } catch (err) {
    toast('Error loading profile', 'error');
  }
}

async function saveContactInfo() {
  try {
    const name = document.getElementById('profile-name').value.trim();
    const email = document.getElementById('profile-email').value.trim();
    const mobile = document.getElementById('profile-mobile').value.trim();
    
    if (!name || !email) {
      toast('Name and email are required', 'error');
      return;
    }
    
    const data = await Api.updateContactInfo({
      name,
      email,
      mobile_number: mobile
    });
    
    photographer = data.photographer;
    Api.savePhotographer(photographer);
    setupSidebarUser();
    toast('Contact information saved! ✅', 'success');
  } catch (err) {
    toast('Error: ' + (err.message || 'Failed to save'), 'error');
  }
}

async function loadPhotographyInfo() {
  try {
    await loadPhotographerProfile();

    const profile = photographer;
    
    // Load specializations
    const specs = profile.specializations || [];
    document.querySelectorAll('.spec-checkbox').forEach(cb => {
      cb.checked = specs.includes(cb.value);
    });
    
    await loadPortfolioPhotos();
  } catch (err) {
    toast('Error loading photography details', 'error');
  }
}

async function savePhotographyInfo() {
  try {
    // Get specializations
    const specializations = [];
    document.querySelectorAll('.spec-checkbox:checked').forEach(cb => {
      specializations.push(cb.value);
    });
    
    const data = await Api.updatePhotographyInfo({
      specializations
    });
    
    photographer = data.photographer;
    Api.savePhotographer(photographer);
    toast('Photography information saved! ✅', 'success');
  } catch (err) {
    toast('Error: ' + (err.message || 'Failed to save'), 'error');
  }
}

function triggerPortfolioPhotoUpload() {
  const input = document.getElementById('portfolio-photo-input');
  if (input) input.click();
}

async function uploadPortfolioPhotos(e) {
  try {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    await Api.uploadPortfolioPhotos(files);

    const updatedProfile = await Api.getProfile();
    photographer = updatedProfile;
    Api.savePhotographer(photographer);

    await loadPortfolioPhotos();
    toast('Portfolio photos uploaded successfully', 'success');
  } catch (err) {
    toast('Error: ' + (err.message || 'Failed to upload photos'), 'error');
  } finally {
    e.target.value = '';
  }
}

async function loadPortfolioPhotos() {
  try {
    const grid = document.getElementById('portfolio-photos-grid');
    if (!grid) return;

    grid.innerHTML = '';

    const res = await Api.getSpecialPhotos();
    const photos = res.special_photos || [];
    const photographerName = photographer.name || 'Photographer';

    if (photos.length === 0) {
      grid.innerHTML = '<p style="grid-column:1/-1;color:var(--white-60);text-align:center;padding:1rem;">No portfolio photos added yet. Upload photos to start building your portfolio.</p>';
      return;
    }

    photos.forEach(photo => {
      const photoDiv = document.createElement('div');
      photoDiv.style.cssText = 'position:relative;border:1px solid rgba(255,255,255,0.12);border-radius:10px;overflow:hidden;background:rgba(0,0,0,0.25);';

      const img = document.createElement('img');
      img.src = `/api/photos/thumbnail/${photo.event_id}/${photo.filename}`;
      img.alt = photo.original_name || 'Portfolio photo';
      img.style.cssText = 'width:100%;height:120px;object-fit:cover;display:block;';
      photoDiv.appendChild(img);

      const badge = document.createElement('div');
      badge.style.cssText = 'position:absolute;left:6px;bottom:6px;padding:0.25rem 0.5rem;border-radius:999px;background:rgba(15,15,25,0.82);color:var(--gold);font-size:0.72rem;font-weight:700;backdrop-filter:blur(6px);';
      badge.textContent = photographerName;
      photoDiv.appendChild(badge);

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.title = 'Remove from portfolio';
      removeBtn.textContent = '✕';
      removeBtn.style.cssText = 'position:absolute;top:6px;right:6px;width:24px;height:24px;border:none;border-radius:999px;background:rgba(10,10,18,0.88);color:var(--white);font-size:0.9rem;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,0.35);';
      removeBtn.onclick = async (event) => {
        event.stopPropagation();
        openPortfolioPhotoRemoveModal(photo);
      };
      photoDiv.appendChild(removeBtn);

      grid.appendChild(photoDiv);
    });
  } catch (err) {
    toast('Error loading photos', 'error');
  }
}

async function loadSpecialPhotos() {
  try {
    await loadPortfolioPhotos();
  } catch (err) {
  }
}
