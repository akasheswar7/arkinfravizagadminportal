/**
 * ARK Infra — Dynamic API Client & Public Page Hydration
 * Seamlessly injects dynamic MongoDB data into the existing HTML/CSS design
 * with graceful fallbacks if backend is offline.
 */

const ARK_API_BASE = "http://localhost:8000/api";

const ArkApi = {
  /**
   * Fetches the current active announcement for the homepage banner.
   */
  async getActiveAnnouncement() {
    try {
      const res = await fetch(`${ARK_API_BASE}/public/announcements/active?t=${Date.now()}`);
      if (res.ok && res.status === 200) {
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
      const res = await fetch(`${ARK_API_BASE}/public/directors?t=${Date.now()}`);
      if (res.ok) {
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
      const res = await fetch(`${ARK_API_BASE}/public/directors/${directorId}/agents?t=${Date.now()}`);
      if (res.ok) {
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
      let url = `${ARK_API_BASE}/public/gallery`;
      if (category && category !== "all") {
        url += `?category=${encodeURIComponent(category)}`;
      }
      const res = await fetch(`${url}&t=${Date.now()}`);
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn("ARK API: Gallery unreachable, displaying static gallery.");
    }
    return [];
  }
};

// Automatic hydration helper for the Homepage
async function hydrateHomepageAnnouncement() {
  const banner = document.getElementById("ceoUpdateBanner");
  const textEl = document.getElementById("ceoUpdateText");
  if (!banner || !textEl) return;

  const ann = await ArkApi.getActiveAnnouncement();
  if (ann && ann.message && ann.message.trim()) {
    textEl.textContent = ann.message.trim();
    banner.style.display = "flex";
  }
}

// Export ArkApi globally
window.ArkApi = ArkApi;
