import Link from "next/link";

export default function NotFound() {
  return (
    <header>
      <h1>Not found</h1>
      <p className="lede">
        That page is not here. The presets are listed on <Link href="/explore">Explore</Link>.
      </p>
    </header>
  );
}
