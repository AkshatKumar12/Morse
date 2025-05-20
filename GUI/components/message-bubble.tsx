import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import type { Message } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Check, CheckCheck } from "lucide-react"

interface MessageBubbleProps {
  message: Message
  isMe: boolean
  contactName: string
  contactAvatar: string
}

export function MessageBubble({ message, isMe, contactName, contactAvatar }: MessageBubbleProps) {
  const formattedTime = new Date(message.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  })

  return (
    <div
      className={cn("flex gap-2 max-w-[80%] animate-message-in", isMe ? "ml-auto flex-row-reverse" : "")}
      style={{
        animationDelay: "0.1s",
      }}
    >
      {!isMe && (
        <Avatar className="h-8 w-8">
          <AvatarImage src={contactAvatar || "/placeholder.svg"} alt={contactName} />
          <AvatarFallback>{contactName.substring(0, 2).toUpperCase()}</AvatarFallback>
        </Avatar>
      )}

      <div
        className={cn(
          "rounded-lg p-3 min-w-[120px] shadow-sm transition-all",
          isMe
            ? "bg-primary text-primary-foreground rounded-tr-none dark:bg-primary/90"
            : "bg-muted rounded-tl-none dark:bg-gray-800",
        )}
      >
        <p className="whitespace-pre-wrap break-words">{message.content}</p>
        <div className={cn("flex items-center gap-1 text-xs mt-1", isMe ? "justify-end" : "")}>
          <span className={isMe ? "text-primary-foreground/70" : "text-muted-foreground"}>{formattedTime}</span>

          {isMe && (
            <span className="text-primary-foreground/70">
              {message.status === "read" ? <CheckCheck className="h-3 w-3" /> : <Check className="h-3 w-3" />}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
