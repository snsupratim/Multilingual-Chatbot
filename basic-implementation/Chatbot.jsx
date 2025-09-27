import { useState, useRef, useEffect, useCallback } from "react";
import {
  MessageCircle,
  Send,
  X,
  ChevronDown,
  ChevronUp,
  Leaf,
  Loader2,
} from "lucide-react";

// --- API & LANGUAGE CONFIGURATION ---
const FASTAPI_API_URL = "http://127.0.0.1:8000/chat"; // Target secured endpoint

// IMPORTANT: Replace this placeholder with your actual MASTER_API_KEY from your .env file
const MASTER_API_KEY = "abcdefgh123456";

const LANGUAGES = {
  English: "en-IN",
  Hindi: "hi-IN",
  Gujarati: "gu-IN",
  Bengali: "bn-IN",
  Kannada: "kn-IN",
  Punjabi: "pa-IN",
};

const SYSTEM_PROMPT =
  "You are a helpful and polite multilingual agricultural assistant. Your responses must be brief, clear, and relevant to farming, crops, weather, and soil health.";

// Helper function to initialize history for all languages
const initializeHistories = () => {
  const initialHistory = {};
  Object.keys(LANGUAGES).forEach((lang) => {
    // Start history with ONLY the system prompt for API compliance
    initialHistory[lang] = [{ role: "system", content: SYSTEM_PROMPT }];
  });
  return initialHistory;
};
// --- END CONFIGURATION ---

const Chatbot = () => {
  // UI State
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Multilingual State
  const [targetLanguage, setTargetLanguage] = useState("English");
  const [allHistories, setAllHistories] = useState(initializeHistories);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState(null);

  // Get the current language's history for display and API calls
  const currentHistory = allHistories[targetLanguage];

  // Auto-scroll function
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Auto-scroll and focus input effect
  useEffect(() => {
    if (isOpen && !isMinimized) {
      scrollToBottom();
      inputRef.current?.focus();
    }
  }, [currentHistory, isOpen, isMinimized]); // Dependency changed to currentHistory

  // Send user message to backend
  const sendMessageToBackend = useCallback(
    async (userMessage) => {
      // Check for key *before* trying to send
      if (MASTER_API_KEY === "your-master-api-key-here") {
        setApiError(
          "Please replace the placeholder key in Chatbot.jsx with your actual MASTER_API_KEY."
        );
        return;
      }

      setLoading(true);
      setApiError(null);

      // 1. Prepare the history array (including the new user message)
      const userMessageObject = { role: "user", content: userMessage };
      const historyToSend = [...currentHistory, userMessageObject];

      // 2. Construct the required API payload
      const payload = {
        messages: historyToSend,
        target_language: targetLanguage, // e.g., "Hindi"
      };

      try {
        const response = await fetch(FASTAPI_API_URL, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            // --- API Key Injection ---
            "X-API-Key": MASTER_API_KEY,
            // -------------------------
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errorData = await response.json();
          const statusText =
            response.status === 401
              ? "Unauthorized (Bad API Key)"
              : `Server error: ${response.status}`;
          throw new Error(errorData.detail || statusText);
        }

        const data = await response.json();
        const botReply = data.reply;

        // 3. Update state with both user and bot messages
        const newHistory = [
          ...historyToSend,
          { text: botReply, sender: "bot", role: "assistant" },
        ];

        setAllHistories((prev) => ({
          ...prev,
          [targetLanguage]: newHistory,
        }));

        return botReply;
      } catch (error) {
        console.error("Server error:", error);
        setApiError(
          error.message || "Server unreachable. Check your FastAPI console."
        );

        // Revert history by removing the failed user message
        const revertedHistory = historyToSend.slice(0, -1);
        setAllHistories((prev) => ({
          ...prev,
          [targetLanguage]: revertedHistory,
        }));

        return "Server unreachable. Please check your FastAPI connection and API key.";
      } finally {
        setLoading(false);
      }
    },
    [currentHistory, targetLanguage]
  );

  // Handle message sending
  const handleSendMessage = async (e) => {
    e.preventDefault();
    const messageText = inputValue.trim();
    if (!messageText || loading) return;

    // Reset error message on new send attempt
    setApiError(null);

    // Update UI immediately with user message (using the temporary format for display)
    const userMessageForDisplay = { text: messageText, sender: "user" };
    const newHistoryWithUser = [...currentHistory, userMessageForDisplay];
    setAllHistories((prev) => ({
      ...prev,
      [targetLanguage]: newHistoryWithUser,
    }));

    setInputValue("");

    // Fetch response from backend
    // Note: The actual state update for the bot reply happens inside sendMessageToBackend
    await sendMessageToBackend(messageText);
  };

  // Filtered history for display (skips system prompt)
  const displayMessages = currentHistory
    .filter((msg) => msg.role !== "system")
    .map((msg) => ({
      // Map the internal structure to the display structure
      text: msg.content || msg.text,
      sender: msg.role === "user" ? "user" : "bot",
    }));

  // Manually inject initial welcome message if no actual conversation has started
  if (displayMessages.length === 0) {
    const welcomeText = `Hello farmer! Welcome to the multilingual assistant. Current language is ${targetLanguage}. How can I help you with your agricultural queries today?`;
    displayMessages.push({ text: welcomeText, sender: "bot" });
  }

  return (
    <div className="fixed bottom-5 right-5 z-50">
      {/* Open Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="bg-green-600 hover:bg-green-700 text-white rounded-full p-4 shadow-lg flex items-center justify-center transition-all duration-200"
          aria-label="Open farmer assistance chat"
        >
          <Leaf size={24} />
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div
          className="bg-white rounded-lg shadow-xl flex flex-col w-80 md:w-96 border border-gray-200 overflow-hidden"
          style={{ transition: "height 0.3s ease" }}
        >
          {/* Header */}
          <div className="bg-green-600 text-white p-4 flex justify-between items-center">
            <h3 className="font-semibold flex items-center gap-2">
              <Leaf size={28} />
              <span>Farmer Support</span>
            </h3>
            <div className="flex gap-2 items-center">
              {/* Language Selector */}
              <select
                value={targetLanguage}
                onChange={(e) => {
                  setTargetLanguage(e.target.value);
                  setApiError(null);
                }}
                className="bg-green-700 text-white text-sm rounded-md p-1 focus:ring-1 focus:ring-white"
                aria-label="Select Chat Language"
              >
                {Object.keys(LANGUAGES).map((lang) => (
                  <option key={lang} value={lang}>
                    {lang}
                  </option>
                ))}
              </select>

              {/* Minimize/Expand Button */}
              <button
                onClick={() => setIsMinimized(!isMinimized)}
                className="hover:bg-green-700 rounded p-1"
                aria-label={isMinimized ? "Expand chat" : "Minimize chat"}
              >
                {isMinimized ? (
                  <ChevronUp size={18} />
                ) : (
                  <ChevronDown size={18} />
                )}
              </button>
              {/* Close Button */}
              <button
                onClick={() => setIsOpen(false)}
                className="hover:bg-green-700 rounded p-1"
                aria-label="Close chat"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Chat Body */}
          {!isMinimized && (
            <>
              <div className="flex-1 p-4 overflow-y-auto max-h-96 bg-green-50">
                {apiError && (
                  <div className="mb-4 p-3 bg-red-100 text-red-700 border border-red-400 rounded-lg text-sm">
                    **API Error:** {apiError}
                  </div>
                )}
                {displayMessages.map((message, index) => (
                  <div
                    key={index}
                    className={`mb-4 ${
                      message.sender === "user"
                        ? "flex justify-end"
                        : "flex justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-3/4 p-3 rounded-lg shadow-sm ${
                        message.sender === "user"
                          ? "bg-green-600 text-white rounded-br-none"
                          : "bg-green-100 text-green-800 rounded-bl-none"
                      }`}
                      style={{ whiteSpace: "pre-wrap", lineHeight: "1.5" }}
                    >
                      {message.text}
                    </div>
                  </div>
                ))}

                {/* Loading Indicator */}
                {loading && (
                  <div className="flex justify-start mb-4">
                    <div className="p-3 bg-green-100 text-green-800 rounded-lg rounded-bl-none flex items-center gap-2">
                      <Loader2 size={16} className="animate-spin" />
                      Translating and generating...
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Input Form */}
              <form
                onSubmit={handleSendMessage}
                className="border-t border-gray-200 p-3 flex"
              >
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder={`Chatting in ${targetLanguage}...`}
                  className="flex-1 border border-gray-300 rounded-l-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                  style={{ color: "black", placeholderColor: "black" }}
                  disabled={loading}
                />
                <button
                  type="submit"
                  className={`text-white px-4 py-2 rounded-r-lg transition-colors ${
                    loading || !inputValue.trim()
                      ? "bg-gray-400 cursor-not-allowed"
                      : "bg-green-600 hover:bg-green-700"
                  }`}
                  disabled={loading || !inputValue.trim()}
                >
                  <Send size={18} />
                </button>
              </form>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default Chatbot;
