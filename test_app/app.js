#!/usr/bin/env node
import React, { useState, useEffect } from 'react';
import { render, Text, Box, useInput, useApp } from 'ink';

const Counter = () => {
	const [counter, setCounter] = useState(0);
	const [message, setMessage] = useState('Press arrow keys to change counter, q to quit');
	const { exit } = useApp();

	useInput((input, key) => {
		if (input === 'q') {
			exit();
		} else if (key.upArrow) {
			setCounter(c => c + 1);
			setMessage('Pressed UP');
		} else if (key.downArrow) {
			setCounter(c => c - 1);
			setMessage('Pressed DOWN');
		} else if (key.leftArrow) {
			setCounter(c => c - 10);
			setMessage('Pressed LEFT (-10)');
		} else if (key.rightArrow) {
			setCounter(c => c + 10);
			setMessage('Pressed RIGHT (+10)');
		} else if (input === 'r') {
			setCounter(0);
			setMessage('Reset counter');
		}
	});

	return (
		<Box flexDirection="column" padding={1}>
			<Box borderStyle="round" borderColor="cyan" padding={1}>
				<Text bold color="green">Terminal Wrapper Test App</Text>
			</Box>
			<Box marginTop={1}>
				<Text>Counter: {counter}</Text>
			</Box>
			<Box marginTop={1}>
				<Text dimColor>{message}</Text>
			</Box>
			<Box marginTop={1}>
				<Text dimColor>
					Controls: ↑/↓ (+/-1) | ←/→ (+/-10) | r (reset) | q (quit)
				</Text>
			</Box>
		</Box>
	);
};

render(<Counter />);
