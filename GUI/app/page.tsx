"use client"

import { useState, useEffect } from "react"
import { MessagingInterface } from "@/components/messaging-interface"
import { SplashScreen } from "@/components/splash-screen"

export default function Home() {
  const [showSplash, setShowSplash] = useState(true)

  useEffect(() => {
    //2.5 s
    const timer = setTimeout(() => {
      setShowSplash(false)
    }, 2500)

    return () => clearTimeout(timer)
  }, [])

  return <main className="min-h-screen">{showSplash ? <SplashScreen /> : <MessagingInterface />}</main>
}
