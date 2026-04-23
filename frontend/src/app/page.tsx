import Link from "next/link";

export default function Home() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-16">
      <h1 className="text-3xl font-semibold mb-4">
        RentRoll<span className="text-garbe-grun">.</span>
      </h1>
      <p className="text-lg text-garbe-blau-60 mb-8 tracking-wide leading-relaxed">
        Transform GARBE Mieterliste CSV files into BVI-compliant XLSX exports.
      </p>
      <Link
        href="/upload"
        className="inline-flex items-center px-5 py-2.5 bg-garbe-grun text-white font-semibold rounded-lg hover:bg-garbe-grun-80 transition-colors tracking-wide"
      >
        Upload CSV
      </Link>
    </div>
  );
}
