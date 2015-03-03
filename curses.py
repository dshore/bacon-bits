#!/usr/bin/env python
import curses
stdscr = curses.initscr()
curses.noecho()
curses.cbreak()
stdscr.keypad(1)

stdscr.addstr(0, 0, "Current mode: Typing mode", curses.A_REVERSE)
stdscr.refresh()

while True:
    c = stdscr.getch()
    if c == ord('p'):
        stdscr.addstr('hello')
    elif c == ord('q'):
        break  # Exit the while()
    elif c == curses.KEY_HOME:
        x = y = 0

curses.nocbreak()
stdscr.keypad(0)
curses.echo()
curses.endwin()
