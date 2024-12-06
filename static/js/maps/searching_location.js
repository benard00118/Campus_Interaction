document.addEventListener("DOMContentLoaded", () => {
  const locations = document.querySelectorAll("#locationList li");
  const searchInput = document.getElementById("search");
  const searchButton = document.getElementById("searchButton");
  const recentSearchesList = document.getElementById("recentSearches");
  const mapFrame = document.getElementById("googleMap");
  const placesContainer = document.getElementById("places-container");

  let recentSearches = [];
  let userLocation = null;
  let locationAttempts = 0;
  const MAX_LOCATION_ATTEMPTS = 3;
  const API_KEY = ""; // Replace with your Google Maps API key

  // Create status indicator
  const createStatusIndicator = () => {
    const statusDiv = document.createElement("div");
    statusDiv.id = "locationStatus";
    statusDiv.style.position = "fixed";
    statusDiv.style.top = "20px";
    statusDiv.style.right = "20px";
    statusDiv.style.padding = "10px 20px";
    statusDiv.style.borderRadius = "5px";
    statusDiv.style.zIndex = "1000";
    document.body.appendChild(statusDiv);
    return statusDiv;
  };

  // Update status message
  const updateStatus = (message, isError = false) => {
    let statusDiv = document.getElementById("locationStatus");
    if (!statusDiv) {
      statusDiv = createStatusIndicator();
    }

    statusDiv.textContent = message;
    statusDiv.style.backgroundColor = isError ? "#ff5252" : "#4CAF50";
    statusDiv.style.color = "white";
    statusDiv.style.opacity = "1";

    if (!isError) {
      setTimeout(() => {
        statusDiv.style.opacity = "0";
        setTimeout(() => statusDiv.remove(), 500);
      }, 3000);
    }
  };

  // Get location using Geolocation API
  const getLocationViaGeolocation = () => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Geolocation is not supported by this browser."));
        return;
      }

      const options = {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      };

      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            accuracy: position.coords.accuracy,
            source: "GPS",
          });
        },
        (error) => {
          reject(error);
        },
        options
      );
    });
  };

  // Get location via IP (fallback)
  const getLocationViaIP = async () => {
    try {
      const response = await fetch("https://ipapi.co/json/");
      const data = await response.json();

      if (data.latitude && data.longitude) {
        return {
          lat: data.latitude,
          lng: data.longitude,
          accuracy: 5000, // IP geolocation is less accurate
          source: "IP",
        };
      }
      throw new Error("Invalid IP geolocation response");
    } catch (error) {
      throw new Error("IP geolocation failed");
    }
  };

  // Initialize map with location
  const initializeMap = (location) => {
    // Store location in session storage
    sessionStorage.setItem("userLocation", JSON.stringify(location));

    // Update map iframe with location and API key
    mapFrame.src = `https://www.google.com/maps/embed/v1/view?key=${API_KEY}&center=${location.lat},${location.lng}&zoom=15`;

    // Update all navigation links with the current location
    const navigationLinks = document.querySelectorAll(".dropdown-content a");
    navigationLinks.forEach((link) => {
      const destination = link.textContent;
      link.href = `https://www.google.com/maps/dir/?api=1&origin=${
        location.lat
      },${location.lng}&destination=${encodeURIComponent(
        destination
      )}&travelmode=walking`;
    });

    // Show success message with location source
    updateStatus(`Location detected via ${location.source}!`);
  };

  // Main location detection flow
  const detectLocation = async () => {
    // Check for stored location first
    const storedLocation = sessionStorage.getItem("userLocation");
    if (storedLocation) {
      const location = JSON.parse(storedLocation);
      updateStatus("Using stored location");
      initializeMap(location);
      return;
    }

    updateStatus("Detecting your location...");

    try {
      // Try Geolocation API first
      const location = await getLocationViaGeolocation();
      initializeMap(location);
    } catch (error) {
      console.warn("Geolocation failed:", error);

      try {
        // Fallback to IP geolocation
        updateStatus("Trying IP-based location...", true);
        const location = await getLocationViaIP();
        initializeMap(location);
      } catch (ipError) {
        console.error("IP geolocation failed:", ipError);

        // Final fallback to default location (Nairobi)
        updateStatus("Using default location", true);
        initializeMap({
          lat: -1.2921,
          lng: 36.8219,
          accuracy: 10000,
          source: "Default",
        });
      }
    }
  };
  // Function to perform a search and update the map
  const performSearch = async (query) => {
    if (!query) return;

    const encodedQuery = encodeURIComponent(query);

    // Update map iframe to search for the query directly, irrespective of user's current location
    mapFrame.src = `https://www.google.com/maps/embed/v1/search?key=${API_KEY}&q=${encodedQuery}`;

    // Update recent searches
    if (!recentSearches.includes(query)) {
      recentSearches.unshift(query);
      if (recentSearches.length > 5) {
        recentSearches.pop();
      }
      updateRecentSearches();
    }
  };

  // Search button click handler
  searchButton.addEventListener("click", () => {
    const query = searchInput.value.trim();
    if (query) {
      performSearch(query);
    }
  });

  // Search input handler
  searchInput.addEventListener("input", (event) => {
    const query = event.target.value.toLowerCase();
    const locationLinks = document.querySelectorAll(".dropdown-content a");

    locationLinks.forEach((link) => {
      const name = link.textContent.toLowerCase();
      link.parentElement.style.display = name.includes(query)
        ? "block"
        : "none";
    });
  });

  // Enter key handler for search
  searchInput.addEventListener("keypress", (event) => {
    if (event.key === "Enter") {
      const query = searchInput.value.trim();
      if (query) {
        performSearch(query);
      }
    }
  });

  // Recent searches management
  const updateRecentSearches = () => {
    recentSearchesList.innerHTML = recentSearches
      .map(
        (search, index) => `
        <div class="search-item">
          <span>${search}</span>
          <button class="delete-btn" data-index="${index}">&times;</button>
        </div>
      `
      )
      .join("");

    // Add delete button handlers
    document.querySelectorAll(".delete-btn").forEach((button) => {
      button.addEventListener("click", (event) => {
        const index = event.target.dataset.index;
        recentSearches.splice(index, 1);
        updateRecentSearches();
        event.stopPropagation();
      });
    });

    // Add click handlers to search items
    document.querySelectorAll(".search-item").forEach((item, index) => {
      item.addEventListener("click", (event) => {
        if (!event.target.classList.contains("delete-btn")) {
          performSearch(recentSearches[index]);
        }
      });
    });
  };

  // Start location detection when page loads
  detectLocation();
});
