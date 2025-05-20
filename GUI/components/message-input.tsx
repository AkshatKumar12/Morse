"use client"

import { cn } from "@/lib/utils"

import { Button } from "@/components/ui/button"
import { Paperclip, Send, Smile } from "lucide-react"
import { useState, type KeyboardEvent } from "react"

interface MessageInputProps {
  onSendMessage: (content: string) => void
}

export function MessageInput({ onSendMessage }: MessageInputProps) {
  const [message, setMessage] = useState("")
  const [isSending, setIsSending] = useState(false)

  const handleSend = () => {
    if (message.trim()) {
      setIsSending(true)
      setTimeout(() => {
        onSendMessage(message)
        setMessage("")
        setIsSending(false)
      }, 300)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="p-4 border-t backdrop-blur-sm bg-background/80">
      <div className="flex items-end gap-2">
        <Button variant="ghost" size="icon" className="rounded-full" title="Attach file">
          <Paperclip className="h-5 w-5" />
        </Button>

        <div className="flex-1 relative">
          <textarea
            className="w-full p-3 pr-10 rounded-lg bg-muted resize-none min-h-[50px] max-h-[150px] overflow-y-auto transition-all duration-200 focus:ring-2 focus:ring-primary/50"
            placeholder="Type a message..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          <Button variant="ghost" size="icon" className="absolute right-2 bottom-2 rounded-full" title="Add emoji">
            <Smile className="h-5 w-5" />
          </Button>
        </div>

        <Button
          size="icon"
          className={cn("rounded-full transition-all duration-300", isSending && "animate-pulse")}
          onClick={handleSend}
          disabled={!message.trim() || isSending}
        >
          <Send className={cn("h-5 w-5 transition-transform", isSending && "translate-x-1 -translate-y-1")} />
        </Button>
      </div>
    </div>
  )
}
