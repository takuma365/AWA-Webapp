import React from 'react';

interface ButtonProps {
  name: string;
  onClick: () => void;
  disabled?: boolean;
}

const Button: React.FC<ButtonProps> = ({ name, onClick, disabled = false }) => {
	return (
		<button 
			className={`w-60 py-2 rounded-full transition ${
				disabled 
					? 'bg-gray-200 text-gray-500 cursor-not-allowed' 
					: 'bg-gray-300 hover:bg-gray-400'
			}`} 
			onClick={onClick}
			disabled={disabled}
		>
			{name}
		</button>
	);
};

export default Button;

