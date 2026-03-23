import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock localStorage globally before any module imports (needed for Zustand persist)
const localStorageStore: Record<string, string> = {}
const localStorageMock = {
  getItem: vi.fn((key: string) => localStorageStore[key] ?? null),
  setItem: vi.fn((key: string, value: string) => { localStorageStore[key] = value }),
  removeItem: vi.fn((key: string) => { delete localStorageStore[key] }),
  clear: vi.fn(() => Object.keys(localStorageStore).forEach(k => delete localStorageStore[k])),
  length: 0,
  key: vi.fn(() => null),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock, writable: true })

// Mock document.documentElement.setAttribute for theme tests
Object.defineProperty(document.documentElement, 'setAttribute', {
  value: vi.fn(),
  writable: true,
})
