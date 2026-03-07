const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const chatLog = document.getElementById("chatLog");
const typingIndicator = document.getElementById("typingIndicator");
const errorText = document.getElementById("errorText");
const connectionStatus = document.getElementById("connectionStatus");

const userIdInput = document.getElementById("userId");
const threadIdInput = document.getElementById("threadId");
const newThreadBtn = document.getElementById("newThreadBtn");
const saveSessionBtn = document.getElementById("saveSessionBtn");
const clearChatBtn = document.getElementById("clearChatBtn");

const STORAGE_KEY = "synapse_frontend_session_v1";
const API_ENDPOINT = "/api/v1/chat";

let isStreaming = false;
let abortController = null;

function makeId(prefix) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function saveSession() {
  const payload = {
    userId: userIdInput.value.trim(),
    threadId: threadIdInput.value.trim(),
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

function loadSession() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    userIdInput.value = makeId("user");
    threadIdInput.value = makeId("thread");
    saveSession();
    return;
  }
  try {
    const parsed = JSON.parse(raw);
    userIdInput.value = parsed.userId || makeId("user");
    threadIdInput.value = parsed.threadId || makeId("thread");
  } catch {
    userIdInput.value = makeId("user");
    threadIdInput.value = makeId("thread");
  }
}

function setError(message = "") {
  if (!message) {
    errorText.classList.add("hidden");
    errorText.textContent = "";
    return;
  }
  errorText.textContent = message;
  errorText.classList.remove("hidden");
}

function setStreamingState(active) {
  isStreaming = active;
  sendBtn.disabled = active;
  messageInput.disabled = active;
  typingIndicator.classList.toggle("hidden", !active);
  typingIndicator.classList.toggle("flex", active);
  sendBtn.textContent = active ? "Streaming..." : "Send";
}

function scrollToBottom() {
  chatLog.scrollTop = chatLog.scrollHeight;
}

function addMessage(role, text = "", timestamp = nowTime()) {
  const wrap = document.createElement("div");
  wrap.className = `message-enter flex ${role === "user" ? "justify-end" : "justify-start"}`;

  const bubble = document.createElement("div");
  bubble.className =
    role === "user"
      ? "max-w-[85%] rounded-2xl rounded-tr-md bg-ocean px-4 py-3 text-sm text-white shadow"
      : "max-w-[85%] rounded-2xl rounded-tl-md border border-ocean/15 bg-paper px-4 py-3 text-sm text-ink shadow-sm";

  const meta = document.createElement("p");
  meta.className = role === "user" ? "mb-1 text-xs text-white/75" : "mb-1 text-xs text-ocean/60";
  meta.textContent = `${role === "user" ? "You" : "SynapseAI"} • ${timestamp}`;

  const content = document.createElement("p");
  content.className = "whitespace-pre-wrap break-words leading-relaxed";
  content.textContent = text;

  bubble.appendChild(meta);
  bubble.appendChild(content);
  wrap.appendChild(bubble);
  chatLog.appendChild(wrap);
  scrollToBottom();

  return content;
}

async function checkConnection() {
  try {
    const response = await fetch("/", { method: "GET" });
    if (!response.ok) throw new Error("offline");
    connectionStatus.textContent = "Frontend Ready";
    connectionStatus.className = "font-semibold text-mint";
  } catch {
    connectionStatus.textContent = "Check Local Server";
    connectionStatus.className = "font-semibold text-amber";
  }
}

async function streamChat(message) {
  const userId = userIdInput.value.trim();
  const threadId = threadIdInput.value.trim();

  if (!userId || !threadId) {
    setError("User ID and Thread ID are required.");
    return;
  }

  saveSession();
  setError("");
  addMessage("user", message);

  const assistantNode = addMessage("assistant", "");
  abortController = new AbortController();

  try {
    setStreamingState(true);

    const response = await fetch(API_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: userId,
        thread_id: threadId,
        message,
      }),
      signal: abortController.signal,
    });

    if (!response.ok || !response.body) {
      throw new Error(`Request failed (${response.status})`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      fullText += chunk;
      assistantNode.textContent = fullText;
      scrollToBottom();
    }

    if (!fullText.trim()) {
      assistantNode.textContent = "No response received from server.";
    }
  } catch (error) {
    if (error.name === "AbortError") {
      assistantNode.textContent = "Response canceled.";
    } else {
      assistantNode.textContent = "Unable to complete the request.";
      setError(`Chat failed: ${error.message}`);
    }
  } finally {
    setStreamingState(false);
    abortController = null;
    messageInput.focus();
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (isStreaming) return;

  const message = messageInput.value.trim();
  if (!message) return;

  messageInput.value = "";
  await streamChat(message);
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

newThreadBtn.addEventListener("click", () => {
  threadIdInput.value = makeId("thread");
  saveSession();
  setError("");
});

saveSessionBtn.addEventListener("click", () => {
  saveSession();
  setError("");
});

clearChatBtn.addEventListener("click", () => {
  chatLog.innerHTML = "";
  setError("");
});

window.addEventListener("beforeunload", () => {
  if (abortController) abortController.abort();
  saveSession();
});

loadSession();
checkConnection();
messageInput.focus();
