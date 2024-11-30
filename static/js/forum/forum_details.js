// Liking
window.toggleLike = async function (postId) {
  const likeElement = document.querySelector(
    `#post-${postId} .stat-item.likes`
  );
  const likeIcon = likeElement.querySelector("i");
  const likeCountElement = likeElement.querySelector("span");
  try {
    const response = await fetch(`/forums/post/${postId}/like/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
          .value,
        "Content-Type": "application/json",
      },
    });
    const data = await response.json();
    if (response.ok) {
      likeCountElement.textContent = data.like_count;
      if (data.status === "liked") {
        likeIcon.classList.add("liked");
      } else {
        likeIcon.classList.remove("liked");
      }
    } else {
      console.error("Failed to toggle like:", data);
    }
  } catch (error) {
    console.error("Error:", error);
  }
};

// Posting
document.addEventListener("DOMContentLoaded", function () {
  const postForm = document.getElementById("post-form");
  const postContainer = document.querySelector(".posts-container");
  const postCountElement = document.getElementById("topics-count");

  function showErrorNotification(message) {
    const notification = document.createElement("div");
    notification.classList.add("error-notification");
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
      notification.style.opacity = 1;
    }, 0);

    setTimeout(() => {
      notification.style.opacity = 0;
      setTimeout(() => {
        notification.remove();
      }, 500);
    }, 4000);
  }

  function makeLinksClickable(postContent) {
    const urlRegex = /https?:\/\/[^\s]+/g;
    return postContent.replace(urlRegex, function (url) {
      return `<a href="${url}" target="_blank">${url}</a>`;
    });
  }

  function toggleMenu(postId) {
    const menu = document.getElementById(`menu-${postId}`);
    menu.classList.toggle("show");
  }

  async function deletePost(postId) {
    try {
      const response = await fetch(`/forums/post/${postId}/delete/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
            .value,
        },
      });

      const data = await response.json();

      if (response.ok) {
        const postElement = document.getElementById(`post-${postId}`);
        if (postElement) {
          postElement.remove();
        }

        updateTopicCount();
      } else {
        console.error("Failed to delete post:", data);
        alert(data.message || "Failed to delete the post");
      }
    } catch (error) {
      console.error("Error:", error);
      alert("An error occurred while deleting the post");
    }
  }

  function sharePost(postId) {
    alert("Share functionality coming soon!");
  }

  function updateTopicCount() {
    fetch("/forums/get_topic_count/")
      .then((response) => response.json())
      .then((data) => {
        if (data.post_count !== undefined) {
          postCountElement.querySelector("span").textContent = data.post_count;
        }
      })
      .catch((error) => {
        console.error("Error fetching topic count:", error);
      });
  }

  postForm.addEventListener("submit", function (e) {
    e.preventDefault();

    const formData = new FormData(postForm);
    const video = formData.get("video");
    const forumId = document.getElementById("post-form-container").dataset
      .forumId;

    if (video && video.size > 10 * 1024 * 1024) {
      showErrorNotification("Video file size must not exceed 10MB.");
      return;
    }

    fetch(`/forums/${forumId}/create_post/`, {
      method: "POST",
      body: formData,
      headers: {
        "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
          .value,
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "error") {
          showErrorNotification(data.message || "Failed to post");
          return;
        }
        if (data.status === "posted") {
          const newPostArticle = document.createElement("article");
          newPostArticle.classList.add("post");
          newPostArticle.id = `post-${data.post_id}`;
          const firstPost = postContainer.querySelector("article");

          let postContent = makeLinksClickable(data.content);
          postContent =
            postContent.length > 60
              ? postContent.substring(0, 60) + "..."
              : postContent;

          newPostArticle.innerHTML = `
            <div class="author__options">
              <div class="post-author">
                <img src="${data.user_profile_pic}" alt="${
            data.username
          } Profile" />
                <div class="author-details">
                  <div class="author-name">${
                    data.username
                  }<span class="post-time" style="margin-left: 3px;"> Just now</span></div>
                  <div class="post-meta">
                    <span class="user-role">${data.user_role}</span>
                    <span class="separator">•</span>
                    <span class="publish-info">Published in ${
                      data.forum_name
                    }</span>
                  </div>
                </div>
              </div>
              <div class="post-options">
                <button class="options-btn" onclick="toggleMenu('${
                  data.post_id
                }')">
                  <i class="fa-solid fa-ellipsis"></i>
                </button>
                <div class="options-menu" id="menu-${data.post_id}">
                  ${
                    data.user_can_delete
                      ? `
                    <button class="menu-item delete-btn" onclick="deletePost('${data.post_id}')">
                      Delete
                    </button>
                  `
                      : ""
                  }
                  <button class="menu-item">
                    <i class="fa-solid fa-flag"></i> Flag
                  </button>
                </div>
              </div>
            </div>
        
            <div class="post-content">
              <p style="display: inline;">${postContent}

              </p>
        
              ${
                data.media_url
                  ? `
                  <div class="media-container">
                    ${
                      data.media_url.includes(".mp4")
                        ? `
                      <video class="video-js vjs-default-skin" controls preload="auto" style="width: 100%; height: 350px; object-fit: cover;">
                        <source src="${data.media_url}" type="video/mp4" />
                      </video>
                    `
                        : `
                      <img src="${data.media_url}" alt="Post media" style="width: 100%; height: auto;" />
                    `
                    }
                  </div>
                `
                  : ""
              }
            </div>
            <div class="post-stats">
              <span class="stat-item likes" onclick="toggleLike('${
                data.post_id
              }')">
                <i class="fa-solid fa-thumbs-up ${
                  data.is_liked ? "liked" : ""
                }"></i>
                <span>${data.likes_count}</span>
              </span>
              <a href="/forums/post/${data.post_id}" style="color: #57606a;">
              <span class="stat-item">
                <i class="fa-regular fa-eye"></i>
                <span>${data.views_count}</span>
              </span>
              </a>
              <a href="/forums/post/${data.post_id}" style="color: #57606a;">
              <span class="stat-item">
                <i class="fa-solid fa-comment" ></i>
                <span>0</span>
              </span>
              </a>
              <span class="stat-item" onclick="sharePost(${data.post_id})">
                <i class="fa-solid fa-share"></i>
                <span>share</span>
              </span>
            </div>
          `;

          postContainer.insertBefore(
            newPostArticle,
            postContainer.querySelector("article")
          );

          if (data.post_count !== undefined) {
            postCountElement.innerHTML = `${data.post_count} <span>Topics</span>`;
          }
          if (data.post_count !== undefined) {
            const postCountHeading =
              document.getElementById("post-count-heading");
            postCountHeading.innerHTML = `${data.post_count} Topics`;
          }

          postForm.reset();
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("Failed to post. Please try again.");
      });
  });

  document.addEventListener("click", function (e) {
    if (e.target.closest(".stat-item.likes")) {
      const postId = e.target.closest(".post").id.replace("post-", "");
      toggleLike(postId);
    }

    if (e.target.closest(".options-btn")) {
      const postId = e.target.closest(".post").id.replace("post-", "");
      toggleMenu(postId);
    }
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const posts = document.querySelectorAll(".post");

  posts.forEach((post) => {
    const postLink = post.querySelector(".post-link");
    const likeButton = post.querySelector(".stat-item.likes");
    const interactiveElements = post.querySelectorAll(
      "button, .stat-item, .options-btn, .options-menu, " +
        "a, input, textarea, .plyr, video, .media-container"
    );

    interactiveElements.forEach((el) => {
      el.addEventListener("click", (e) => {
        e.stopPropagation();
      });
    });

    if (likeButton) {
      likeButton.addEventListener("click", (e) => {
        e.stopPropagation();
      });
    }

    post.addEventListener("click", (e) => {
      if (
        postLink &&
        !e.target.closest(".stat-item, .options-menu, button, a, .plyr, video")
      ) {
        window.location.href = postLink.getAttribute("href");
      }
    });

    post.addEventListener("mouseenter", () => {
      post.classList.add("post-hover");
    });

    post.addEventListener("mouseleave", () => {
      post.classList.remove("post-hover");
    });
  });
});

// JavaScript to handle switching between image and video input, ensuring only one media type can be uploaded at a time.
document.addEventListener("DOMContentLoaded", function () {
  const imageField = document.querySelector(".image-field");
  const videoField = document.querySelector(".video-field");
  const imageInput = document.querySelector('input[name="image"]');
  const videoInput = document.querySelector('input[name="video"]');
  const messageContainer = document.createElement("div");
  document.body.appendChild(messageContainer);

  function showMessage(message) {
    messageContainer.textContent = message;
    messageContainer.style.position = "fixed";
    messageContainer.style.bottom = "10px";
    messageContainer.style.left = "50%";
    messageContainer.style.transform = "translateX(-50%)";
    messageContainer.style.padding = "10px";
    messageContainer.style.backgroundColor = "rgba(0, 0, 0, 0.7)";
    messageContainer.style.color = "white";
    messageContainer.style.borderRadius = "5px";
    messageContainer.style.fontSize = "14px";
    messageContainer.style.opacity = "1";
    messageContainer.style.transition = "opacity 0.5s ease-out"; // Transition for fade-out

    setTimeout(() => {
      messageContainer.style.opacity = "0";
      setTimeout(() => {
        messageContainer.textContent = "";
      }, 500);
    }, 3000);
  }

  imageInput.addEventListener("change", function () {
    if (videoInput.files.length > 0) {
      videoInput.value = "";
      showMessage(
        "Video file removed. Only one file (image or video) can be submitted."
      );
    }
  });

  videoInput.addEventListener("change", function () {
    if (imageInput.files.length > 0) {
      imageInput.value = "";
      showMessage(
        "Image file removed. Only one file (image or video) can be submitted."
      );
    }

    const videoFile = videoInput.files[0];
    if (videoFile && videoFile.type !== "video/mp4") {
      showMessage("Please upload a .mp4 video file.");
      videoInput.value = "";
    }
  });
});

document.addEventListener("DOMContentLoaded", function () {
  const textarea = document.querySelector("#post-form textarea");

  if (textarea) {
    textarea.addEventListener("keydown", function (e) {
      if (e.key === "Tab") {
        e.preventDefault();
        const start = this.selectionStart;
        const end = this.selectionEnd;
        this.value =
          this.value.substring(0, start) + "\t" + this.value.substring(end);

        this.selectionStart = this.selectionEnd = start + 1;
      }
    });
  }
});

// Searching for Posts
document.addEventListener("DOMContentLoaded", function () {
  const searchInput = document.getElementById("forum-search-input");
  const suggestionsContainer = document.getElementById("search-suggestions");
  const forumId = searchInput.getAttribute("data-forum-id");

  let debounceTimer;
  let cachedSuggestions = [];
  let lastQuery = "";

  searchInput.addEventListener("focus", function () {
    searchInput.classList.add("focused");
    if (
      cachedSuggestions.length > 0 &&
      searchInput.value.trim() === lastQuery
    ) {
      displaySuggestions(cachedSuggestions);
    }
  });

  searchInput.addEventListener("blur", function () {
    searchInput.classList.remove("focused");

    setTimeout(() => {
      suggestionsContainer.style.display = "none";
    }, 200);
  });

  searchInput.addEventListener("input", function () {
    clearTimeout(debounceTimer);

    const query = this.value.trim();
    if (query.length < 2) {
      suggestionsContainer.innerHTML = "";
      suggestionsContainer.style.display = "none";
      cachedSuggestions = [];
      lastQuery = "";
      return;
    }

    debounceTimer = setTimeout(() => {
      if (query === lastQuery) {
        displaySuggestions(cachedSuggestions);
        return;
      }

      fetch(
        `/forums/search/posts/?q=${encodeURIComponent(
          query
        )}&forum_id=${forumId}`
      )
        .then((response) => response.json())
        .then((data) => {
          if (data.suggestions.length === 0) {
            displayNoResults(query);
            return;
          }

          cachedSuggestions = data.suggestions;
          lastQuery = query;
          displaySuggestions(data.suggestions);
        })
        .catch((error) => {
          console.error("Search error:", error);
          displayErrorMessage();
        });
    }, 300);
  });

  function displayNoResults(query) {
    suggestionsContainer.innerHTML = "";
    const noResultsElement = document.createElement("div");
    noResultsElement.classList.add("no-results");
    noResultsElement.innerHTML = `
      <div style="padding: 15px; text-align: center; color: #6c757d;">
        <p>No results found for "<strong>${escapeHtml(query)}</strong>"</p>
        <small>Try different keywords or check your spelling</small>
      </div>
    `;
    suggestionsContainer.appendChild(noResultsElement);
    suggestionsContainer.style.display = "block";
    applyContainerStyles();
  }

  function displayErrorMessage() {
    suggestionsContainer.innerHTML = "";
    const errorElement = document.createElement("div");
    errorElement.classList.add("search-error");
    errorElement.innerHTML = `
      <div style="padding: 15px; text-align: center; color: #dc3545;">
        <p>An error occurred while searching</p>
        <small>Please try again later</small>
      </div>
    `;
    suggestionsContainer.appendChild(errorElement);
    suggestionsContainer.style.display = "block";
    applyContainerStyles();
  }

  function escapeHtml(unsafe) {
    return unsafe
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function displaySuggestions(suggestions) {
    suggestionsContainer.innerHTML = "";

    suggestions.forEach((suggestion) => {
      const suggestionElement = document.createElement("div");
      suggestionElement.classList.add("search-suggestion");

      suggestionElement.innerHTML = `
  <a href="${
    suggestion.url
  }" class="suggestion-link" style="display: flex; align-items: center;">
    ${
      suggestion.media
        ? `<div class="media-container" style="margin-right: 10px; position: relative; width: 50px; height: 50px;">
             ${
               suggestion.media.endsWith(".mp4") ||
               suggestion.media.endsWith(".webm") ||
               suggestion.media.endsWith(".ogg")
                 ? `<div style="width: 50px; height: 50px; background: #000; display: flex; justify-content: center; align-items: center; border-radius: 5px;">
                      <i class="fa fa-play" style="color: white; font-size: 20px;"></i>
                    </div>`
                 : `<img src="${suggestion.media}" alt="Media" style="width: 50px; height: 50px; object-fit: cover; border-radius: 5px;" />`
             }
           </div>`
        : ""
    }
    <div class="suggestion-content">
      <strong>${suggestion.title}</strong>
      <small>created by ${suggestion.author} ${suggestion.created_at}</small>
    </div>
  </a>
`;
      suggestionElement.addEventListener("mouseover", () => {
        suggestionElement.style.backgroundColor = "#e9ecef";
      });

      suggestionElement.addEventListener("mouseout", () => {
        suggestionElement.style.backgroundColor = "#f8f9fa";
      });

      suggestionElement.addEventListener("click", () => {
        window.location.href = suggestion.url;
      });

      suggestionsContainer.appendChild(suggestionElement);
    });

    applyContainerStyles();
  }

  function applyContainerStyles() {
    suggestionsContainer.style.display = "block";
    suggestionsContainer.style.position = "absolute";
    suggestionsContainer.style.width = searchInput.offsetWidth + "px";
    suggestionsContainer.style.backgroundColor = "#fff";
    suggestionsContainer.style.border = "1px solid #dee2e6";
    suggestionsContainer.style.boxShadow = "0 4px 6px rgba(0,0,0,0.1)";
    suggestionsContainer.style.maxHeight = "300px";
    suggestionsContainer.style.overflowY = "auto";
    suggestionsContainer.style.zIndex = "4";
  }

  document.addEventListener("click", function (event) {
    if (
      !suggestionsContainer.contains(event.target) &&
      event.target !== searchInput
    ) {
      suggestionsContainer.style.display = "none";
    }
  });

  window.addEventListener("resize", function () {
    suggestionsContainer.style.width = searchInput.offsetWidth + "px";
  });
});
