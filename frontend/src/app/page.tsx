import Link from "next/link";

export default function Home() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-16">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">RentRoll</h1>
      <p className="text-lg text-gray-600 mb-8">
        Transform GARBE Mieterliste CSV files into BVI-compliant XLSX exports.
      </p>
      <Link
        href="/upload"
        className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
      >
        Upload CSV
      </Link>
    </div>
  );
}
