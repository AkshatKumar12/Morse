import { MessageSquare } from "lucide-react"

export function SplashScreen() {
  return (
    <div className="h-screen w-full flex flex-col items-center justify-center bg-primary">
      <div className="animate-fade-in-up flex flex-col items-center">
        <div className="relative">
          <div className="h-24 w-24 rounded-full bg-primary-foreground flex items-center justify-center mb-6 animate-pulse">
            <MessageSquare className="h-12 w-12 text-primary" />
          </div>
          <div className="absolute -top-2 -right-2 h-5 w-5 rounded-full bg-green-500 animate-ping" />
        </div>
        <h1 className="text-4xl font-bold text-primary-foreground tracking-wider animate-fade-in">Morse</h1>
        <p className="text-primary-foreground/70 mt-2 animate-fade-in-delay">Secure Messaging</p>
      </div>
    </div>
  )
}
