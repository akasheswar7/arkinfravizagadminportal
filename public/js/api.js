/**
 * ARK Infra — Dynamic API Client & Public Page Hydration
 * Seamlessly injects dynamic MongoDB data into the existing HTML/CSS design
 * with graceful fallbacks if backend is offline.
 */

const CLOUD_API_BASE = "https://arkinfravizagadminportal.vercel.app/api";
let ARK_API_BASE = CLOUD_API_BASE;

if (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") && window.location.port !== "") {
  ARK_API_BASE = "http://localhost:8000/api";
} else {
  ARK_API_BASE = CLOUD_API_BASE;
}

async function arkSafeFetch(urlPath) {
  try {
    const res = await fetch(`${ARK_API_BASE}${urlPath}`);
    if (res.ok) return res;
    if (res.status === 404 && ARK_API_BASE !== CLOUD_API_BASE) {
      ARK_API_BASE = CLOUD_API_BASE;
      return await fetch(`${ARK_API_BASE}${urlPath}`);
    }
    return res;
  } catch (err) {
    if (ARK_API_BASE !== CLOUD_API_BASE) {
      console.warn("Local API offline, auto-switching to live Cloud API:", CLOUD_API_BASE);
      ARK_API_BASE = CLOUD_API_BASE;
      try {
        return await fetch(`${ARK_API_BASE}${urlPath}`);
      } catch (cloudErr) {
        return null;
      }
    }
    return null;
  }
}

const ArkApi = {
  /**
   * Fetches the current active announcement for the homepage banner.
   */
  async getActiveAnnouncement() {
    try {
      const res = await arkSafeFetch(`/public/announcements/active?t=${Date.now()}`);
      if (res && res.ok && res.status === 200) {
        return await res.json();
      }
    } catch (e) {
      console.warn("ARK API: Announcement offline or unreachable, using fallback.");
    }
    return null;
  },

  /**
   * Fetches all directors and their assigned agent counts.
   */
  async getDirectors() {
    try {
      const res = await arkSafeFetch(`/public/directors?t=${Date.now()}`);
      if (res && res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn("ARK API: Directors offline or unreachable.");
    }
    return [];
  },

  /**
   * Fetches all agents assigned to a specific director.
   */
  async getAgentsByDirector(directorId) {
    try {
      const res = await arkSafeFetch(`/public/directors/${directorId}/agents?t=${Date.now()}`);
      if (res && res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn(`ARK API: Agents for director ${directorId} unreachable.`);
    }
    return [];
  },

  /**
   * Fetches published gallery photos by category.
   */
  async getGallery(category = "all") {
    try {
      const params = new URLSearchParams();
      if (category && category !== "all") {
        params.append("category", category);
      }
      params.append("t", Date.now().toString());
      const res = await arkSafeFetch(`/public/gallery?${params.toString()}`);
      if (res && res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn("ARK API: Gallery unreachable, displaying static gallery.");
    }
    return [];
  },

  /**
   * Fetches published projects for public display.
   */
  async getProjects(statusFilter = "all") {
    try {
      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== "all") {
        params.append("status_filter", statusFilter);
      }
      params.append("t", Date.now().toString());
      const res = await arkSafeFetch(`/public/projects?${params.toString()}`);
      if (res && res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn("ARK API: Projects unreachable, using static fallback.");
    }
    return [];
  }
};

// Automatic hydration helper for the Homepage Announcement Banner
async function hydrateHomepageAnnouncement() {
  const banner = document.getElementById("ceoUpdateBanner");
  const textEl = document.getElementById("ceoUpdateText");
  const badgeEl = document.getElementById("ceoUpdateBadge") || document.querySelector(".ceo-badge");
  if (!banner || !textEl) return;

  const ann = await ArkApi.getActiveAnnouncement();
  if (ann && ann.message && ann.message.trim()) {
    if (badgeEl && ann.title && ann.title.trim()) {
      badgeEl.textContent = ann.title.trim();
    }
    textEl.textContent = ann.message.trim();
    banner.style.display = "flex";
  }
}

// Export ArkApi globally
window.ArkApi = ArkApi;

