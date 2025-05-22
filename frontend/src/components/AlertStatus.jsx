import React from "react";

export default function AlertStatus({ status }) {
  if (!status) return null;
  return (
    <div className={`p-2 rounded text-white mt-2 ${status === "sent" ? "bg-green-600" : "bg-yellow-500"}`}>
      {status === "sent" ? "Alert sent!" : "Alert scheduled"}
    </div>
  );
}
