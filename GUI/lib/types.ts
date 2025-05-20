export interface Contact {
  id: string
  name: string
  avatar: string
  status: "online" | "offline"
  lastMessage: string
  lastMessageTime: string
}

export interface Message {
  id: string
  content: string
  senderId: string
  timestamp: Date
  status: "sent" | "delivered" | "read"
}
