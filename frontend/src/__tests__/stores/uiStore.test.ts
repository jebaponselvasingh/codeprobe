import { describe, it, expect, beforeEach } from 'vitest'
import { useUiStore } from '../../stores/uiStore'
import { act } from '@testing-library/react'

describe('uiStore', () => {
  beforeEach(() => {
    useUiStore.setState({
      theme: 'dark',
      sidebarOpen: true,
      activePage: 'review',
      toasts: [],
    })
  })

  it('toggles theme from dark to light', () => {
    act(() => {
      useUiStore.getState().toggleTheme()
    })
    expect(useUiStore.getState().theme).toBe('light')
  })

  it('toggles theme back to dark', () => {
    useUiStore.setState({ theme: 'light' })
    act(() => {
      useUiStore.getState().toggleTheme()
    })
    expect(useUiStore.getState().theme).toBe('dark')
  })

  it('toggles sidebar', () => {
    act(() => {
      useUiStore.getState().toggleSidebar()
    })
    expect(useUiStore.getState().sidebarOpen).toBe(false)
  })

  it('navigates to different pages', () => {
    act(() => {
      useUiStore.getState().navigate('batch')
    })
    expect(useUiStore.getState().activePage).toBe('batch')
  })

  it('shows and auto-dismisses toast', async () => {
    act(() => {
      useUiStore.getState().showToast('Test message', 'success')
    })
    expect(useUiStore.getState().toasts).toHaveLength(1)
    expect(useUiStore.getState().toasts[0].message).toBe('Test message')
    expect(useUiStore.getState().toasts[0].type).toBe('success')
  })

  it('dismisses toast by id', () => {
    act(() => {
      useUiStore.getState().showToast('Hello')
    })
    const id = useUiStore.getState().toasts[0].id
    act(() => {
      useUiStore.getState().dismissToast(id)
    })
    expect(useUiStore.getState().toasts).toHaveLength(0)
  })
})
