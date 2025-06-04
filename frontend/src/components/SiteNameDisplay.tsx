
import { useParams } from 'react-router-dom';

const SiteNameDisplay = () => {
  const { site } = useParams<{ site: string }>();

  return (
    <div>
      <h1>Selected Site: {site}</h1>
      {/* Additional content */}
    </div>
  );
};

export default SiteNameDisplay;