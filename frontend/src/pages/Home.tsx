import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <div className="home">
      <h1>HookahBook</h1>
      <p className="subtitle">Бронирование и заказ кальянов онлайн</p>

      <div className="actions">
        <Link to="/booking" className="btn btn-primary">
          Забронировать стол
        </Link>
      </div>
    </div>
  );
}
