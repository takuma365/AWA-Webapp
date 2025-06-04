interface ButtonProps {
  name: string;
  onClick: () => void;
}


const Button: React.FC<ButtonProps> = ({ name, onClick }) => {
	return (
		<button className="w-60 py-2 rounded-full bg-gray-300 hover:bg-gray-400 transition" onClick={onClick}>
			{name}
			</button>
	);
};

export default Button;

