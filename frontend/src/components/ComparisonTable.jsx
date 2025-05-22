import React from "react";

export default function ComparisonTable({ comparisons }) {
  if (!comparisons || comparisons.length === 0) return null;
  return (
    <div className="bg-white rounded shadow p-4 mt-4">
      <h3 className="font-semibold mb-2">Available on Other Platforms</h3>
      <table className="w-full text-left">
        <thead>
          <tr>
            <th className="py-1">Platform</th>
            <th className="py-1">Price</th>
            <th className="py-1">Link</th>
          </tr>
        </thead>
        <tbody>
          {comparisons.map((item, idx) => (
            <tr key={idx}>
              <td>{item.platform}</td>
              <td>₹{item.price ?? "Not Available"}</td>
              <td>
                {item.url ? (
                  <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">View</a>
                ) : (
                  "—"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
