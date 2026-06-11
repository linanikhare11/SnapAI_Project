/* SnapAI — API Client (Clean & Correct Version) */

const API_BASE = window.location.origin + '/api';

const Api = {

  // ── Token Management ─────────────────────────────
  getToken() {
    return localStorage.getItem('snapai_token');
  },

  setToken(token) {
    localStorage.setItem('snapai_token', token);
  },

  clearToken() {
    localStorage.removeItem('snapai_token');
    localStorage.removeItem('snapai_photographer');
  },

  savePhotographer(data) {
    localStorage.setItem('snapai_photographer', JSON.stringify(data));
  },

  getPhotographer() {
    const raw = localStorage.getItem('snapai_photographer');
    return raw ? JSON.parse(raw) : null;
  },

  // ── Headers ─────────────────────────────────────
  headers(isForm = false) {
    const headers = {};
    const token = this.getToken();
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    if (!isForm) headers['Content-Type'] = 'application/json';

    return headers;
  },

  // ── Core Request ────────────────────────────────
  async request(method, path, body = null, isForm = false) {
    class ApiError extends Error {
      constructor(message, status, data) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.data = data;
      }
    }

    const options = {
      method,
      headers: this.headers(isForm)
    };

    if (body) {
      options.body = isForm ? body : JSON.stringify(body);
    }
    
    let res;
    try {
      res = await fetch(`${API_BASE}${path}`, options);
    } catch (fetchErr) {
      throw new ApiError(`Network error: ${fetchErr.message}`, 0, null);
    }

    let data = {};
    try {
      data = await res.json();
    } catch (e) {
    }

    // Handle unauthorized
    if (res.status === 401) {
      this.clearToken();
      window.location.href = '/login';
      throw new ApiError('Session expired. Please login again.', 401, data);
    }

    if (!res.ok) {
      const errMsg = data.error || data.message || `HTTP ${res.status}`;
      throw new ApiError(errMsg, res.status, data);
    }

    return data;
  },

  // ── Auth ───────────────────────────────────────
  async register(payload) {
    const data = await this.request('POST', '/auth/register', payload);
    this.setToken(data.token);
    this.savePhotographer(data.photographer);
    return data;
  },

  async login(email, password) {
    const data = await this.request('POST', '/auth/login', { email, password });
    this.setToken(data.token);
    this.savePhotographer(data.photographer);
    return data;
  },

  async getMe() {
    return this.request('GET', '/auth/me');
  },

  async updateProfile(payload) {
    return this.request('PUT', '/auth/update-profile', payload);
  },

  // ── Photographer Profile ───────────────────────
  async getProfile() {
    return this.request('GET', '/profile/me');
  },

  async updateContactInfo(payload) {
    const data = await this.request('PUT', '/profile/me/contact', payload);
    if (data.photographer) {
      this.savePhotographer(data.photographer);
    }
    return data;
  },

  async updatePhotographyInfo(payload) {
    const data = await this.request('PUT', '/profile/me/photography', payload);
    if (data.photographer) {
      this.savePhotographer(data.photographer);
    }
    return data;
  },

  async getSpecialPhotos() {
    return this.request('GET', '/profile/me/special-photos');
  },

  async getProfileChatMessages() {
    return this.request('GET', '/profile/me/chat');
  },

  async sendProfileChatMessage(message, sender = 'photographer') {
    return this.request('POST', '/profile/me/chat', { message, sender });
  },

  async listPortfolioSourcePhotos() {
    return this.request('GET', '/profile/me/photos');
  },

  async uploadPortfolioPhotos(files) {
    const form = new FormData();
    files.forEach(file => form.append('photos', file));
    return this.request('POST', '/profile/me/special-photos/upload', form, true);
  },

  async addSpecialPhoto(photoId) {
    return this.request('POST', '/profile/me/special-photos', { photo_id: photoId });
  },

  async removeSpecialPhoto(photoId) {
    return this.request('DELETE', `/profile/me/special-photos/${photoId}`);
  },

  async getPhotographerPublicProfile(photographerId) {
    return this.request('GET', `/profile/${photographerId}`);
  },

  // ── Events ─────────────────────────────────────
  async listEvents() {
    return this.request('GET', '/events/');
  },

  async createEvent(payload) {
    return this.request('POST', '/events/', payload);
  },

  async getEvent(id) {
    return this.request('GET', `/events/${id}`);
  },

  async updateEvent(id, payload) {
    return this.request('PUT', `/events/${id}`, payload);
  },

  async deleteEvent(id) {
    return this.request('DELETE', `/events/${id}`);
  },

  async eventStats(id) {
    return this.request('GET', `/events/${id}/stats`);
  },

  async setCoverPhoto(eventId, photoId) {
    return this.request('POST', `/events/${eventId}/set-cover`, { photo_id: photoId });
  },

  async dashSummary() {
    return this.request('GET', '/events/dashboard/summary');
  },

  // ── Photos ─────────────────────────────────────
  async listPhotos(eventId, page = 1) {
    return this.request(
      'GET',
      `/photos/list/${eventId}?page=${page}&per_page=50`
    );
  },

  async deletePhoto(photoId) {
    return this.request('DELETE', `/photos/delete/${photoId}`);
  },

  async startIndexing(eventId) {
    return this.request('POST', `/photos/index/${eventId}`);
  },

  async indexingStatus(eventId) {
    return this.request('GET', `/photos/indexing-status/${eventId}`);
  },

  // ── Upload Photos (with progress) ───────────────
  async uploadPhotos(eventId, files, onProgress) {
    const form = new FormData();
    files.forEach(file => form.append('photos', file));

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      xhr.open('POST', `${API_BASE}/photos/upload/${eventId}`);

      const token = this.getToken();
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
          const percent = Math.round((e.loaded / e.total) * 100);
          onProgress(percent);
        }
      };

      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText);

          if (xhr.status >= 400) {
            reject(new Error(data.error || 'Upload failed'));
          } else {
            resolve(data);
          }
        } catch {
          reject(new Error('Invalid server response'));
        }
      };

      xhr.onerror = () => reject(new Error('Network error'));

      xhr.send(form);
    });
  },

  // ── Guest ──────────────────────────────────────
  async getPublicEvent(slug, pin = '') {
    return this.request(
      'GET',
      `/guest/event/${slug}${pin ? '?pin=' + pin : ''}`
    );
  },

  async getEventPhotos(slug, page = 1, pin = '') {
    return this.request(
      'GET',
      `/guest/event/${slug}/photos?page=${page}&per_page=48${pin ? '&pin=' + pin : ''}`
    );
  },

  async verifyPin(slug, pin) {
    return this.request('POST', '/guest/verify-pin', { slug, pin });
  },

  async findMyPhotos(slug, selfieBlob, pin = '') {
    const form = new FormData();
    form.append('selfie', selfieBlob, 'selfie.jpg');
    form.append('consent', 'true');

    if (pin) form.append('pin', pin);

    return this.request(
      'POST',
      `/guest/event/${slug}/find-me`,
      form,
      true
    );
  },

  async detectFace(slug, selfieBlob, pin = '') {
    const form = new FormData();
    form.append('selfie', selfieBlob, 'selfie.jpg');
    form.append('consent', 'true');

    if (pin) form.append('pin', pin);

    return this.request(
      'POST',
      `/guest/event/${slug}/detect-face`,
      form,
      true
    );
  },

  // ── Themes ─────────────────────────────────────
  async uploadThemeImage(eventType, file) {
    const form = new FormData();
    form.append('image', file);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      xhr.open('POST', `${API_BASE}/themes/upload/${eventType}`);

      const token = this.getToken();
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText);

          if (xhr.status >= 400) {
            reject(new Error(data.error || 'Upload failed'));
          } else {
            resolve(data);
          }
        } catch {
          reject(new Error('Invalid server response'));
        }
      };

      xhr.onerror = () => reject(new Error('Network error'));

      xhr.send(form);
    });
  },

  async getThemeImage(eventType) {
    try {
      return `${API_BASE}/themes/${eventType}`;
    } catch (err) {
      return null;
    }
  },

  async listThemeImages(eventType) {
    return this.request('GET', `/themes/list/${eventType}`);
  }
};


// ── Toast System ─────────────────────────────────
function toast(message, type = 'info') {
  let container = document.getElementById('toast-container');

  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerText = message;

  container.appendChild(el);

  setTimeout(() => el.remove(), 4000);
}


// ── Auth Guard ───────────────────────────────────
function requireAuth() {
  if (!Api.getToken()) {
    window.location.href = '/login';
    return false;
  }
  return true;
}


// ── Navbar Scroll Effect ─────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const nav = document.querySelector('.navbar');

  if (nav) {
    window.addEventListener('scroll', () => {
      nav.classList.toggle('scrolled', window.scrollY > 50);
    });
  }
});