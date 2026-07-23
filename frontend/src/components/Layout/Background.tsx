import './Background.css';

export default function Background() {
  return (
    <>
      <div className="bg-decorations" aria-hidden="true">
        <img className="bg-star bg-star-1" src="/decor/star.png" alt="" />
        <img className="bg-star bg-star-2" src="/decor/star.png" alt="" />
        <img className="bg-star bg-star-3" src="/decor/star.png" alt="" />
        <img className="bg-star bg-star-4" src="/decor/star.png" alt="" />
        <img className="bg-book" src="/decor/open-book.png" alt="" />
        <span className="bg-cloud bg-cloud-1" />
        <span className="bg-cloud bg-cloud-2" />
      </div>
      <a
        className="asset-credit"
        href="https://pngimg.com/"
        target="_blank"
        rel="noreferrer"
        title="装饰素材采用 CC BY-NC 4.0 许可"
      >
        装饰素材：PNGimg · CC BY-NC 4.0
      </a>
    </>
  );
}
