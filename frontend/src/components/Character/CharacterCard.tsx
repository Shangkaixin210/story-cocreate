import type { Character } from '../../api/endpoints';
import './CharacterCard.css';

interface CharacterCardProps {
  character: Character;
  onSelect?: (character: Character) => void;
  onDelete?: (character: Character) => void;
  selected?: boolean;
}

const AVATAR_EMOJI: Record<string, string> = {
  astronaut: '🧑‍🚀',
  dragon: '🐲',
  fairy: '🧚',
  pirate: '🏴‍☠️',
  robot: '🤖',
  explorer: '🧭',
  wizard: '🧙',
  mermaid: '🧜‍♀️',
};

const AVATAR_LABELS: Record<string, string> = {
  astronaut: '小宇航员',
  dragon: '小龙',
  fairy: '小精灵',
  pirate: '小海盗',
  robot: '机器人',
  explorer: '探险家',
  wizard: '小巫师',
  mermaid: '美人鱼',
};

export default function CharacterCard({ character, onSelect, onDelete, selected }: CharacterCardProps) {
  const emoji = AVATAR_EMOJI[character.avatar_type] || '🌟';
  const label = AVATAR_LABELS[character.avatar_type] || character.avatar_type;

  return (
    <div
      className={`character-card ${selected ? 'character-card-selected' : ''}`}
      onClick={() => onSelect?.(character)}
      style={{ borderColor: selected ? character.avatar_color : undefined }}
    >
      <div className="character-avatar" style={{ backgroundColor: character.avatar_color + '20' }}>
        <span className="character-emoji">{emoji}</span>
      </div>
      <div className="character-info">
        <h3 className="character-nickname">{character.nickname}</h3>
        <span className="character-type">{label}</span>
      </div>
      {onDelete && (
        <button
          className="character-delete"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(character);
          }}
          title="删除角色"
        >
          🗑️
        </button>
      )}
    </div>
  );
}

export { AVATAR_EMOJI, AVATAR_LABELS };
