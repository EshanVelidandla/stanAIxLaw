import React from 'react'
import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import { ArrowUp, Globe, BrainCog } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const cn = (...classes) => classes.filter(Boolean).join(' ')

// Scrollbar styles for the textarea
if (typeof document !== 'undefined') {
  const s = document.createElement('style')
  s.innerText = `
    .pg-input::-webkit-scrollbar { width: 5px; }
    .pg-input::-webkit-scrollbar-track { background: transparent; }
    .pg-input::-webkit-scrollbar-thumb { background: #1E3358; border-radius: 3px; }
  `
  document.head.appendChild(s)
}

const TooltipProvider = TooltipPrimitive.Provider
const Tooltip       = TooltipPrimitive.Root
const TooltipTrigger = TooltipPrimitive.Trigger
const TooltipContent = React.forwardRef(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Portal>
    <TooltipPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        'z-[200] rounded-lg border border-[#1E3358] bg-[#070F1E] px-3 py-1.5',
        'text-xs text-[#7A9BBF] shadow-lg',
        'animate-in fade-in-0 zoom-in-95',
        'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
        className
      )}
      {...props}
    />
  </TooltipPrimitive.Portal>
))
TooltipContent.displayName = 'TooltipContent'

const Divider = () => (
  <div className="relative h-5 w-px mx-1 flex-shrink-0">
    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#C9A84C]/40 to-transparent rounded-full" />
  </div>
)

export function PromptInputBox({ onSend, isLoading, placeholder = 'Ask a patent litigation question…', initialValue = '' }) {
  const [input, setInput] = React.useState(initialValue)
  const [showLive, setShowLive] = React.useState(false)
  const [showDeep, setShowDeep] = React.useState(false)
  const textareaRef = React.useRef(null)

  // Auto-resize textarea
  React.useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [input])

  // Sync if initialValue changes
  React.useEffect(() => {
    if (initialValue) setInput(initialValue)
  }, [initialValue])

  const handleSubmit = () => {
    if (!input.trim() || isLoading) return
    onSend?.(input.trim(), showDeep)
    setInput('')
    setShowLive(false)
    setShowDeep(false)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const hasContent = input.trim() !== ''

  return (
    <TooltipProvider delayDuration={400}>
      <div className={cn(
        'rounded-3xl border p-2 transition-all duration-300 w-full',
        'bg-[#070F1E] border-[#1E3358]',
        'shadow-[0_8px_40px_rgba(0,0,0,0.6),0_0_0_1px_rgba(30,51,88,0.3)]',
        'focus-within:border-[#2A4570] focus-within:shadow-[0_8px_40px_rgba(0,0,0,0.6),0_0_20px_rgba(201,168,76,0.08)]',
        isLoading && 'opacity-60 pointer-events-none',
      )}>
        <textarea
          ref={textareaRef}
          className={cn(
            'pg-input w-full bg-transparent px-3 py-2.5 text-base resize-none',
            'text-[#E8EDF5] placeholder:text-[#4A6B8A] text-center placeholder:text-center',
            'focus:outline-none focus:ring-0 border-none',
            'min-h-[44px] max-h-[200px] leading-relaxed',
          )}
          rows={1}
          placeholder={placeholder}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />

        <div className="flex items-center justify-between gap-2 px-1 pt-1">
          {/* Mode toggles */}
          <div className="flex items-center gap-0.5">
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={() => { setShowLive(p => !p); setShowDeep(false) }}
                  className={cn(
                    'rounded-full transition-all duration-200 flex items-center gap-1.5 px-2.5 py-1 h-8 text-xs font-medium border',
                    showLive
                      ? 'bg-[#4A9EDB]/12 border-[#4A9EDB]/60 text-[#4A9EDB]'
                      : 'bg-transparent border-transparent text-[#4A6B8A] hover:text-[#7A9BBF] hover:bg-[#0F1E35]'
                  )}
                >
                  <motion.span
                    animate={{ rotate: showLive ? 360 : 0, scale: showLive ? 1.15 : 1 }}
                    transition={{ type: 'spring', stiffness: 260, damping: 22 }}
                    className="flex items-center"
                  >
                    <Globe className="w-3.5 h-3.5" />
                  </motion.span>
                  <AnimatePresence initial={false}>
                    {showLive && (
                      <motion.span
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 'auto', opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        transition={{ duration: 0.18 }}
                        className="overflow-hidden whitespace-nowrap"
                      >
                        Live Cases
                      </motion.span>
                    )}
                  </AnimatePresence>
                </button>
              </TooltipTrigger>
              <TooltipContent>Search live case law via Midpage API</TooltipContent>
            </Tooltip>

            <Divider />

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={() => { setShowDeep(p => !p); setShowLive(false) }}
                  className={cn(
                    'rounded-full transition-all duration-200 flex items-center gap-1.5 px-2.5 py-1 h-8 text-xs font-medium border',
                    showDeep
                      ? 'bg-[#8B5CF6]/12 border-[#8B5CF6]/60 text-[#A78BFA]'
                      : 'bg-transparent border-transparent text-[#4A6B8A] hover:text-[#7A9BBF] hover:bg-[#0F1E35]'
                  )}
                >
                  <motion.span
                    animate={{ rotate: showDeep ? 360 : 0, scale: showDeep ? 1.15 : 1 }}
                    transition={{ type: 'spring', stiffness: 260, damping: 22 }}
                    className="flex items-center"
                  >
                    <BrainCog className="w-3.5 h-3.5" />
                  </motion.span>
                  <AnimatePresence initial={false}>
                    {showDeep && (
                      <motion.span
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 'auto', opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        transition={{ duration: 0.18 }}
                        className="overflow-hidden whitespace-nowrap"
                      >
                        Deep Analysis
                      </motion.span>
                    )}
                  </AnimatePresence>
                </button>
              </TooltipTrigger>
              <TooltipContent>Extended precedent chain analysis</TooltipContent>
            </Tooltip>
          </div>

          {/* Submit button */}
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={handleSubmit}
                disabled={!hasContent || isLoading}
                className={cn(
                  'h-9 w-9 rounded-full flex items-center justify-center transition-all duration-200 flex-shrink-0',
                  hasContent && !isLoading
                    ? [
                        'bg-gradient-to-br from-[#C9A84C] to-[#E8C76A] text-[#050A14]',
                        'shadow-[0_2px_12px_rgba(201,168,76,0.35)]',
                        'hover:shadow-[0_4px_20px_rgba(201,168,76,0.55)] hover:scale-105 active:scale-95',
                      ]
                    : 'bg-[#0F1E35] text-[#2A4570] cursor-not-allowed',
                )}
              >
                <ArrowUp className="h-4 w-4" strokeWidth={2.5} />
              </button>
            </TooltipTrigger>
            <TooltipContent side="left">
              {hasContent ? 'Analyze (Enter)' : 'Type a question first'}
            </TooltipContent>
          </Tooltip>
        </div>
      </div>
    </TooltipProvider>
  )
}
