// frontend/app/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { io } from 'socket.io-client';

const socket = io("http://localhost:8000"); // Make sure your Python server runs on this port

export default function Home() {
  const [msg, setMsg] = useState("");
  const [messages, setMessages] = useState<string[]>([]);

  useEffect(() => {
    socket.on("receive", (data) => {
      setMessages((prev) => [...prev, "Friend: " + data.text]);
    });

    return () => {
      socket.off("receive");
    }
  }, []);

  const send = () => {
    if (msg.trim() === "") return;
    socket.emit("message", msg);
    setMessages((prev) => [...prev, "You: " + msg]);
    setMsg("");
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen p-4 bg-gray-900 text-white">
      <h1 className="text-2xl mb-4 font-bold">Morse Chat</h1>
      <div className="w-full max-w-md bg-gray-800 p-4 rounded shadow-md">
        <div className="h-64 overflow-y-auto bg-black text-green-400 p-2 rounded mb-4">
          {messages.map((m, i) => (
            <div key={i}>{m}</div>
          ))}
        </div>
        <div className="flex">
          <input
            value={msg}
            onChange={(e) => setMsg(e.target.value)}
            className="flex-1 p-2 rounded-l bg-gray-700 border border-gray-600 focus:outline-none"
            placeholder="Type your message"
          />
          <button
            onClick={send}
            className="bg-blue-600 px-4 rounded-r hover:bg-blue-700"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
