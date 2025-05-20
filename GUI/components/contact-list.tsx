"use client"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import type { Contact } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Search } from "lucide-react"
import { useState } from "react"

interface ContactListProps {
  contacts: Contact[]
  selectedContact: Contact | null
  onSelectContact: (contact: Contact) => void
  onCloseSidebar?: () => void
}

export function ContactList({ contacts, selectedContact, onSelectContact, onCloseSidebar }: ContactListProps) {
  const [searchQuery, setSearchQuery] = useState("")

  const filteredContacts = contacts.filter((contact) => contact.name.toLowerCase().includes(searchQuery.toLowerCase()))

  const handleContactClick = (contact: Contact) => {
    onSelectContact(contact)
    if (onCloseSidebar) {
      onCloseSidebar()
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b">
        <h1 className="text-xl font-bold mb-4">Messages</h1>
        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search contacts"
            className="w-full pl-8 py-2 bg-muted rounded-md text-sm"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {filteredContacts.length > 0 ? (
          filteredContacts.map((contact) => (
            <div
              key={contact.id}
              className={cn(
                "flex items-center gap-3 p-3 cursor-pointer hover:bg-accent transition-colors",
                selectedContact?.id === contact.id && "bg-accent",
              )}
              onClick={() => handleContactClick(contact)}
            >
              <div className="relative">
                <Avatar>
                  <AvatarImage src={contact.avatar || "/placeholder.svg"} alt={contact.name} />
                  <AvatarFallback>{contact.name.substring(0, 2).toUpperCase()}</AvatarFallback>
                </Avatar>
                {contact.status === "online" && (
                  <span className="absolute bottom-0 right-0 h-3 w-3 rounded-full bg-green-500 border-2 border-background"></span>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-baseline">
                  <h3 className="font-medium truncate">{contact.name}</h3>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">{contact.lastMessageTime}</span>
                </div>
                <p className="text-sm text-muted-foreground truncate">{contact.lastMessage}</p>
              </div>
            </div>
          ))
        ) : (
          <div className="p-4 text-center text-muted-foreground">No contacts found</div>
        )}
      </div>
    </div>
  )
}
