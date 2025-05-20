"use client"

import { useState } from "react"
import { ContactList } from "@/components/contact-list"
import { ChatArea } from "@/components/chat-area"
import { MessageInput } from "@/components/message-input"
import type { Contact, Message } from "@/lib/types"
import { initialContacts, initialMessages } from "@/lib/mock-data"
import { useMobile } from "@/hooks/use-mobile"
import { Button } from "@/components/ui/button"
import { Menu, Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

export function MessagingInterface() {
  const [contacts, setContacts] = useState<Contact[]>(initialContacts)
  const [messages, setMessages] = useState<Record<string, Message[]>>(initialMessages)
  const [selectedContact, setSelectedContact] = useState<Contact | null>(initialContacts[0])
  const [showSidebar, setShowSidebar] = useState(true)
  const isMobile = useMobile()
  const { theme, setTheme } = useTheme()

  const handleSendMessage = (content: string) => {
    if (!selectedContact || !content.trim()) return

    const newMessage: Message = {
      id: `msg-${Date.now()}`,
      content,
      senderId: "me",
      timestamp: new Date(),
      status: "sent",
    }

    setMessages((prev) => ({
      ...prev,
      [selectedContact.id]: [...(prev[selectedContact.id] || []), newMessage],
    }))
  }

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark")
  }

  return (
    <div className="flex h-screen bg-background transition-colors duration-300">
      {}
      {isMobile && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-2 left-2 z-10"
          onClick={() => setShowSidebar(!showSidebar)}
        >
          <Menu className="h-5 w-5" />
        </Button>
      )}

      {}
      <Button variant="ghost" size="icon" className="absolute top-2 right-2 z-10" onClick={toggleTheme}>
        {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
      </Button>

      {}
      <div
        className={`${
          isMobile
            ? `fixed inset-y-0 left-0 z-50 w-72 transform transition-transform duration-300 ease-in-out ${
                showSidebar ? "translate-x-0" : "-translate-x-full"
              } bg-background border-r`
            : "w-80 border-r"
        }`}
      >
        <ContactList
          contacts={contacts}
          selectedContact={selectedContact}
          onSelectContact={setSelectedContact}
          onCloseSidebar={() => isMobile && setShowSidebar(false)}
        />
      </div>

      {/* Main chat area */}
      <div className={`flex-1 flex flex-col ${isMobile && showSidebar ? "opacity-50" : ""}`}>
        {selectedContact ? (
          <>
            <ChatArea contact={selectedContact} messages={messages[selectedContact.id] || []} />
            <MessageInput onSendMessage={handleSendMessage} />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-muted-foreground">Select a contact to start messaging</p>
          </div>
        )}
      </div>
    </div>
  )
}
