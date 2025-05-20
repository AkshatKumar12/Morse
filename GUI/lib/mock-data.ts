import type { Contact, Message } from "./types"

export const initialContacts: Contact[] = [
  {
    id: "1",
    name: "Akshat Kumar(Team Lead)",
    avatar: "/placeholder.svg?height=40&width=40",
    status: "online",
    lastMessage: "",
    lastMessageTime: "",
  },
  {
    id: "2",
    name: "Anmol Bisht",
    avatar: "/placeholder.svg?height=40&width=40",
    status: "offline",
    lastMessage: "",
    lastMessageTime: "",
  },
  {
    id: "3",
    name: "Om",
    avatar: "/placeholder.svg?height=40&width=40",
    status: "online",
    lastMessage: "",
    lastMessageTime: "",
  },
  {
    id: "4",
    name: "Ajay",
    avatar: "/placeholder.svg?height=40&width=40",
    status: "offline",
    lastMessage: "",
    lastMessageTime: "",
  },
]

// Create empty message records for each contact
export const initialMessages: Record<string, Message[]> = {
  "1": [],
  "2": [],
  "3": [],
  "4": [],
  "5": [],
  "6": [],
  "7": [],
}
