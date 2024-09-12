/*
 * Class created by Copilot
 */
 
using System;
using System.Threading;

public class ConsoleSpinner
{
    private int _currentAnimationFrame;
    private readonly string[] _animationFrames = { "/", "-", "\\", "|" };
    private readonly int _delay;
    private bool _active;
    private Thread _thread;

    public ConsoleSpinner(int delay = 100)
    {
        _delay = delay;
        _thread = new Thread(Spin);
    }

    public void Start()
    {
        _active = true;
        _thread.Start();
    }

    public void Stop()
    {
        _active = false;
        _thread.Join();
    }

    private void Spin()
    {
        while (_active)
        {
            Turn();
            Thread.Sleep(_delay);
        }
    }

    private void Turn()
    {
        Console.Write(_animationFrames[_currentAnimationFrame]);
        Console.SetCursorPosition(Console.CursorLeft - 1, Console.CursorTop);
        _currentAnimationFrame++;
        if (_currentAnimationFrame == _animationFrames.Length)
        {
            _currentAnimationFrame = 0;
        }
    }
}